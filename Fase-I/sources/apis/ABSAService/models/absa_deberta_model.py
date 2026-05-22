"""
Backend ABSA: NLI (detección) + DeBERTa ATSC (sentimiento) + BERTopic (dinámicos).

Pipeline:
  Tópicos FIJOS (por review):
    1. Segmentar en oraciones.
    2. NLI zero-shot: "¿Esta oración menciona el aspecto X?" → entailment score.
    3. DeBERTa ATSC (fragmento, aspecto) → sentimiento.

  Tópicos DINÁMICOS (batch sobre todo el corpus):
    4. BERTopic descubre clusters semánticos en las oraciones del corpus.
    5. Se filtran clusters solapantes con tópicos fijos (cosine >= 0.65).
    6. DeBERTa ATSC predice el sentimiento del fragmento representativo.

Modelos:
  - Detección:   cross-encoder/nli-deberta-v3-small    (NLI, zero-shot-classification)
  - Sentimiento: yangheng/deberta-v3-base-absa-v1.1    (transformers pipeline, ATSC)
  - Embeddings:  paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers, BERTopic)
  - Topic model: BERTopic + UMAP + HDBSCAN

Variables de configuración:
    NLI_MODEL                — modelo HuggingFace para zero-shot NLI
    NLI_ENTAILMENT_THRESHOLD — umbral de entailment para declarar tópico mencionado
    SENTENCE_MODEL           — encoder para embeddings (BERTopic)
    DEBERTA_ABSA_MODEL       — modelo ATSC HuggingFace
    BERTOPIC_MIN_TOPIC_SIZE  — tamaño mínimo de cluster BERTopic (default 3)
"""

import logging
import re
import unicodedata
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as cosine_sim
from bertopic import BERTopic
from umap import UMAP
from hdbscan import HDBSCAN
from transformers import pipeline as hf_pipeline
from sklearn.feature_extraction.text import CountVectorizer
from models.absa_llm_model import ABSAResultado, TopicoFijoResultado, TopicoDinamicoResultado

logger = logging.getLogger(__name__)


_RE_ORACION      = re.compile(r"(?<=[.!?])\s+")
_SENTIMIENTO_MAP = {"Positive": "positivo", "Negative": "negativo", "Neutral": "neutro"}
_HIPOTESIS_DETECCION = "Este texto menciona {} del hotel."

def _construir_stopwords() -> list[str]:
    try:
        from nltk.corpus import stopwords as nltk_sw
        base = set(nltk_sw.words("spanish"))
    except LookupError:
        import nltk
        nltk.download("stopwords", quiet=True)
        from nltk.corpus import stopwords as nltk_sw
        base = set(nltk_sw.words("spanish"))

    # Términos específicos de reviews hoteleras que no son aspectos
    extra = {
        # Sustantivos genéricos — no son aspectos de hotel
        "hotel", "habitación", "cuarto", "estancia", "visita",
        "persona", "personas", "gente", "cliente", "clientes",
        "día", "días", "noche", "noches", "vez", "veces",
        "cosa", "cosas", "problema", "problemas", "detalle", "detalles",
        "lugar", "sitio", "parte", "lado", "zona",
        # Adjetivos de valoración genérica
        "excelente", "perfecto", "perfecta", "perfectos", "perfectas",
        "bueno", "buena", "buenos", "buenas", "malo", "mala", "malos", "malas",
        "mejor", "peor", "pésimo", "pésima", "horrible", "terrible",
        "increíble", "fantástico", "fantástica", "espantoso",
        "lento", "lenta", "rápido", "rápida",
        # Adjetivos descriptivos no-aspecto
        "limpio", "limpia", "limpios", "limpias",
        "espacioso", "espaciosa", "espaciosos", "espaciosas",
        "cómodo", "cómoda", "cómodos", "cómodas",
        "bonito", "bonita", "bonitos", "bonitas",
        "grande", "pequeño", "pequeña", "nuevo", "nueva",
        # Adverbios
        "realmente", "totalmente", "absolutamente", "bastante", "demasiado",
        # Verbos frecuentes en reviews que no son aspectos
        "gustó", "gustaron", "encantó", "pareció", "resultó",
        "necesitaba", "necesitó", "necesita", "necesitan",
        "funcionaba", "funcionó", "funciona", "funcionaban",
        "encontré", "encontramos", "encontraba",
        "quedaba", "quedó", "queda",
        "tenía", "tenían", "tiene", "tienen",
        "podía", "pude", "pudimos", "pudieron",
        "debería", "deberían",
    }
    
    # Remover tildes uniformemente para que el vectorizer haga match exacto (al usar strip_accents="unicode")
    stopwords_list = sorted(base | extra)
    def _sin_tildes(texto: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
        
    return list({_sin_tildes(w) for w in stopwords_list})


_STOPWORDS_ES = _construir_stopwords()


class ABSADebertaModel:
    """
    Tópicos fijos: NLI zero-shot (detección) + DeBERTa ATSC (sentimiento).
    Tópicos dinámicos: BERTopic sobre el corpus completo (batch) + DeBERTa ATSC.
    """

    def __init__(self, config):
        logger.info("Cargando pipeline NLI (zero-shot): %s", config.NLI_MODEL)
        self._nli = hf_pipeline("zero-shot-classification", model=config.NLI_MODEL)

        logger.info("Cargando SentenceTransformer: %s", config.SENTENCE_MODEL)
        self._encoder = SentenceTransformer(config.SENTENCE_MODEL)

        logger.info("Cargando DeBERTa ATSC: %s", config.DEBERTA_ABSA_MODEL)
        self._absa = hf_pipeline(
            "text-classification",
            model=config.DEBERTA_ABSA_MODEL,
            tokenizer=config.DEBERTA_ABSA_MODEL,
        )

        self._entailment_threshold       = config.NLI_ENTAILMENT_THRESHOLD
        self._nli_max_fixed_per_review   = config.NLI_MAX_FIXED_PER_REVIEW
        self._bertopic_min_size          = config.BERTOPIC_MIN_TOPIC_SIZE
        self._bertopic_min_dynamic_score = config.BERTOPIC_MIN_DYNAMIC_SCORE
        self._bertopic_max_per_review    = config.BERTOPIC_MAX_DYNAMIC_PER_REVIEW
        self._deberta_model_name         = config.DEBERTA_ABSA_MODEL
        self._emb_topicos_cache: dict[tuple, "np.ndarray"] = {}

    @property
    def version(self) -> str:
        return f"deberta-nli-{self._deberta_model_name.split('/')[-1]}"

    # ── Interfaz pública — por review (fijos solamente) ───────────────────────

    def analizar(self, texto: str, topicos_fijos: list[dict]) -> ABSAResultado:
        """
        Detecta tópicos fijos en una sola review.
        Los tópicos dinámicos se descubren en analizar_batch (corpus completo).
        """
        oraciones = _segmentar(texto)
        if not oraciones:
            return ABSAResultado(topicos_fijos=[_topico_no_mencionado(t) for t in topicos_fijos])
        return ABSAResultado(topicos_fijos=self._detectar_topicos_fijos(oraciones, topicos_fijos))

    # ── Interfaz pública — batch (fijos + BERTopic dinámicos) ────────────────

    def analizar_batch(
        self,
        reviews: list[dict],
        topicos_fijos: list[dict],
        topicos_adicionales: list[dict] | None = None,
    ) -> list[ABSAResultado]:
        """
        Procesa todas las reviews del corpus en una sola llamada.
        BERTopic descubre tópicos dinámicos sobre el conjunto de oraciones.

        Args:
            reviews:             Lista de dicts con al menos 'review_id' y 'texto_limpio'.
            topicos_fijos:       Lista de dicts con 'id', 'slug' y 'nombre'.
            topicos_adicionales: Tópicos adicionales ya existentes en BD (opcional).

        Returns:
            Lista de ABSAResultado en el mismo orden que reviews.
        """
        # ── 1. Segmentar y construir corpus ───────────────────────────────────
        corpus_oraciones: list[str] = []
        indices_por_review: dict[int, list[int]] = {}

        for i, review in enumerate(reviews):
            inicio    = len(corpus_oraciones)
            oraciones = _segmentar(review.get("texto_limpio") or "")
            indices_por_review[i] = list(range(inicio, inicio + len(oraciones)))
            corpus_oraciones.extend(oraciones)

        # ── 2. Embeddings en una sola pasada (para BERTopic) ──────────────────
        if corpus_oraciones:
            emb_corpus = self._encoder.encode(
                corpus_oraciones, batch_size=64, show_progress_bar=False
            )
        else:
            emb_corpus = np.empty((0, self._encoder.get_sentence_embedding_dimension()))

        emb_topicos = self._codificar_topicos(topicos_fijos)

        # ── 3. Tópicos fijos por review (NLI) ────────────────────────────────
        resultados_fijos: list[list[TopicoFijoResultado]] = []
        for i in range(len(reviews)):
            indices = indices_por_review[i]
            if not indices:
                resultados_fijos.append([_topico_no_mencionado(t) for t in topicos_fijos])
                continue
            oraciones_i = [corpus_oraciones[k] for k in indices]
            resultados_fijos.append(self._detectar_topicos_fijos(oraciones_i, topicos_fijos))

        # ── 4. Tópicos dinámicos con BERTopic ────────────────────────────────
        dinamicos_por_review = self._extraer_dinamicos_batch(
            corpus_oraciones, emb_corpus, indices_por_review, emb_topicos,
            len(reviews), topicos_adicionales or [],
        )

        return [
            ABSAResultado(topicos_fijos=fijos, topicos_dinamicos=dinamicos)
            for fijos, dinamicos in zip(resultados_fijos, dinamicos_por_review)
        ]

    # ── Tópicos fijos (NLI) ───────────────────────────────────────────────────

    def _detectar_topicos_fijos(
        self,
        oraciones: list[str],
        topicos_fijos: list[dict],
    ) -> list[TopicoFijoResultado]:
        """
        Para cada tópico:
          1. Puntúa todas las oraciones contra la hipótesis del tópico en batch.
          2. La oración con mayor score de entailment es el fragmento candidato.
          3. Si ese score supera el umbral → mencionado; DeBERTa ATSC predice sentimiento.
        """
        if not topicos_fijos or not oraciones:
            return [_topico_no_mencionado(t) for t in topicos_fijos]

        resultado = []

        for topico in topicos_fijos:
            nombre = topico["nombre"]

            try:
                scores_nli = self._nli(
                    oraciones,
                    candidate_labels=[nombre],
                    hypothesis_template=_HIPOTESIS_DETECCION,
                    multi_label=True,
                )
                entailment_scores = [r["scores"][0] for r in scores_nli]
            except Exception as e:
                logger.warning(
                    "NLI falló para tópico '%s': %s. Marcando como no mencionado.", nombre, e
                )
                resultado.append(_topico_no_mencionado(topico))
                continue

            max_score = max(entailment_scores)
            best_idx  = entailment_scores.index(max_score)

            if max_score >= self._entailment_threshold:
                fragmento = oraciones[best_idx]
                resultado.append(TopicoFijoResultado(
                    slug=topico["slug"],
                    mencionado=True,
                    sentimiento=self._deberta_sentimiento(fragmento, nombre),
                    score_topico=round(max_score, 3),
                    fragmento=fragmento,
                ))
            else:
                resultado.append(_topico_no_mencionado(topico))

        # Mantener solo los top N tópicos mencionados por entailment score
        mencionados = [r for r in resultado if r.mencionado]
        if len(mencionados) > self._nli_max_fixed_per_review:
            mencionados.sort(key=lambda r: r.score_topico or 0, reverse=True)
            slugs_excluidos = {r.slug for r in mencionados[self._nli_max_fixed_per_review:]}
            resultado = [
                _topico_no_mencionado(t) if t["slug"] in slugs_excluidos else r
                for t, r in zip(topicos_fijos, resultado)
            ]

        return resultado

    # ── Tópicos dinámicos con BERTopic (batch) ────────────────────────────────

    def _extraer_dinamicos_batch(
        self,
        corpus_oraciones: list[str],
        emb_corpus,
        indices_por_review: dict[int, list[int]],
        emb_topicos,
        n_reviews: int,
        topicos_adicionales: list[dict] | None = None,
    ) -> list[list[TopicoDinamicoResultado]]:
        """
        Ejecuta BERTopic sobre el corpus completo de oraciones.
        Devuelve una lista de listas de TopicoDinamicoResultado, una por review.
        """
        dinamicos: list[list[TopicoDinamicoResultado]] = [[] for _ in range(n_reviews)]

        n = len(corpus_oraciones)
        min_size = self._bertopic_min_size

        if n < min_size * 2:
            logger.warning(
                "Corpus demasiado pequeño (%d oraciones, mínimo %d) para BERTopic.",
                n, min_size * 2,
            )
            return dinamicos

        try:
            umap_model = UMAP(
                n_neighbors=min(15, n - 1),
                n_components=min(5, n - 1),
                min_dist=0.0,
                metric="cosine",
                random_state=42,
            )
            hdbscan_model = HDBSCAN(
                min_cluster_size=min_size,
                metric="euclidean",
                prediction_data=True,
            )

            vectorizer = CountVectorizer(
                stop_words=_STOPWORDS_ES,
                ngram_range=(1, 3),
                min_df=max(1, min(2, n // 20)),
                strip_accents="unicode",
            )

            topic_model = BERTopic(
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                vectorizer_model=vectorizer,
                language="multilingual",
                calculate_probabilities=False,
                verbose=False,
            )
            topics, _ = topic_model.fit_transform(corpus_oraciones, embeddings=emb_corpus)
        except Exception as e:
            logger.error("BERTopic falló: %s. No se extraen tópicos dinámicos.", e)
            return dinamicos

        # ── Filtrar clusters válidos (batch encode) ───────────────────────────
        candidatos: dict[int, str] = {}
        for topic_id in sorted(set(topics)):
            if topic_id == -1:
                continue
            keywords = topic_model.get_topic(topic_id)
            if keywords:
                candidatos[topic_id] = keywords[0][0]

        topicos_validos: dict[int, str] = {}
        if candidatos and emb_topicos.shape[0] > 0:
            ids       = list(candidatos.keys())
            nombres   = list(candidatos.values())
            emb_cands = self._encoder.encode(nombres, show_progress_bar=False)
            sims      = cosine_sim(emb_cands, emb_topicos).max(axis=1)
            for topic_id, nombre, sim in zip(ids, nombres, sims):
                logger.info("BERTopic cluster_%d '%s': sim_max_fijos=%.3f", topic_id, nombre, float(sim))
                if sim < 0.65:
                    topicos_validos[topic_id] = nombre
        else:
            topicos_validos = dict(candidatos)

        if not topicos_validos:
            logger.info("BERTopic: ningún cluster pasó el filtro de solapamiento.")
            return dinamicos

        logger.info("BERTopic: %d clusters válidos tras filtro: %s", len(topicos_validos), topicos_validos)

        # ── Matching contra tópicos adicionales existentes ────────────────────
        # topico_identidad[topic_id] = (nombre_final, slug_final)
        # Si el cluster es semánticamente similar a uno existente, reutiliza nombre+slug.
        topico_identidad: dict[int, tuple[str, str]] = {
            tid: (nombre, "") for tid, nombre in topicos_validos.items()
        }
        if topicos_adicionales:
            ids_v     = list(topicos_validos.keys())
            noms_v    = list(topicos_validos.values())
            noms_ad   = [t["nombre"] for t in topicos_adicionales]
            emb_v     = self._encoder.encode(noms_v,  show_progress_bar=False)
            emb_ad    = self._encoder.encode(noms_ad, show_progress_bar=False)
            sims_ad   = cosine_sim(emb_v, emb_ad)          # (n_clusters, n_adicionales)
            for i, (tid, nom_cluster) in enumerate(zip(ids_v, noms_v)):
                best_j   = int(sims_ad[i].argmax())
                best_sim = float(sims_ad[i, best_j])
                if best_sim >= 0.75:
                    existente = topicos_adicionales[best_j]
                    logger.info(
                        "BERTopic cluster '%s' → tópico existente '%s' (slug='%s', sim=%.3f)",
                        nom_cluster, existente["nombre"], existente["slug"], best_sim,
                    )
                    topico_identidad[tid] = (existente["nombre"], existente["slug"])
                else:
                    logger.info(
                        "BERTopic cluster '%s': sin match en adicionales (best_sim=%.3f) → nuevo tópico.",
                        nom_cluster, best_sim,
                    )

        # ── Mapa oración → review ─────────────────────────────────────────────
        oracion_a_review: dict[int, int] = {
            sent_idx: review_idx
            for review_idx, indices in indices_por_review.items()
            for sent_idx in indices
        }

        # ── Mejor oración por (review, topic) ────────────────────────────────
        mejor: dict[tuple[int, int], str] = {}
        for sent_idx, topic_id in enumerate(topics):
            if topic_id not in topicos_validos:
                continue
            review_idx = oracion_a_review.get(sent_idx)
            if review_idx is None:
                continue
            key = (review_idx, topic_id)
            if key not in mejor:
                mejor[key] = corpus_oraciones[sent_idx]

        logger.info("BERTopic: %d pares (review, cluster) con oración representativa.", len(mejor))

        if not mejor:
            logger.warning("BERTopic: 'mejor' vacío — ninguna oración asignada a clusters válidos.")
            return dinamicos

        # ── Construir TopicoDinamicoResultado (batch encode) ──────────────────
        pares      = list(mejor.items())
        fragmentos = [f for _, f in pares]
        noms       = [topico_identidad[tid][0] for (_, tid), _ in pares]
        slugs      = [topico_identidad[tid][1] for (_, tid), _ in pares]

        emb_frags = self._encoder.encode(fragmentos, show_progress_bar=False)
        emb_noms  = self._encoder.encode(noms,       show_progress_bar=False)
        scores    = [_norm_cosine(float(s)) for s in np.diag(cosine_sim(emb_frags, emb_noms))]

        logger.info(
            "BERTopic scores (fragmento↔nombre): min=%.3f max=%.3f umbral=%.2f",
            min(scores), max(scores), self._bertopic_min_dynamic_score,
        )

        # Agrupar candidatos por review, filtrar por score mínimo
        candidatos_por_review: dict[int, list[tuple[float, str, str, str]]] = {}
        for i, ((review_idx, _), fragmento) in enumerate(pares):
            score = scores[i]
            if score < self._bertopic_min_dynamic_score:
                continue
            candidatos_por_review.setdefault(review_idx, []).append(
                (score, noms[i], fragmento, slugs[i])
            )

        # Conservar solo los top N por score para cada review
        for review_idx, candidatos in candidatos_por_review.items():
            candidatos.sort(key=lambda x: x[0], reverse=True)
            for score, nombre, fragmento, slug in candidatos[:self._bertopic_max_per_review]:
                dinamicos[review_idx].append(TopicoDinamicoResultado(
                    nombre=nombre.title() if not slug else nombre,
                    sentimiento=self._deberta_sentimiento(fragmento, nombre),
                    score_topico=round(score, 3),
                    fragmento=fragmento,
                    slug=slug,
                ))

        return dinamicos

    # ── Sentimiento con DeBERTa ATSC ──────────────────────────────────────────

    def _deberta_sentimiento(self, fragmento: str, aspecto: str) -> str:
        try:
            resultado = self._absa(fragmento[:512], text_pair=aspecto)
            return _SENTIMIENTO_MAP.get(resultado[0]["label"], "neutro")
        except Exception as e:
            logger.warning(
                "DeBERTa ATSC falló para aspecto='%s': %s. Retornando 'neutro'.", aspecto, e
            )
            return "neutro"

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _codificar_topicos(self, topicos_fijos: list[dict]) -> "np.ndarray":
        """Codifica tópicos fijos como frases ancla para el filtro de solapamiento. Cachea por lista de nombres."""
        if not topicos_fijos:
            return np.empty((0, self._encoder.get_sentence_embedding_dimension()))
        key = tuple(t["nombre"] for t in topicos_fijos)
        if key not in self._emb_topicos_cache:
            self._emb_topicos_cache[key] = self._encoder.encode(
                [_ancla_topico(n) for n in key], show_progress_bar=False
            )
        return self._emb_topicos_cache[key]


# ── Helpers de módulo ─────────────────────────────────────────────────────────

def _ancla_topico(nombre: str) -> str:
    n = nombre.lower()
    return f"El hotel tiene {n}. Opinión sobre el {n}."


def _segmentar(texto: str) -> list[str]:
    if not texto or not texto.strip():
        return []
    oraciones = [s.strip() for s in _RE_ORACION.split(texto) if len(s.strip()) > 10]
    return oraciones or [texto]


def _norm_cosine(sim: float) -> float:
    return float(np.clip((sim + 1) / 2, 0.0, 1.0))


def _topico_no_mencionado(topico: dict) -> TopicoFijoResultado:
    return TopicoFijoResultado(
        slug=topico["slug"], mencionado=False,
        sentimiento=None, score_topico=None, fragmento=None,
    )
