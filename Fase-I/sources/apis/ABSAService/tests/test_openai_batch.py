import json
import unittest

from routes.validators import validar_body_sincronizar_batch
from services.openai_batch_client import OpenAIBatchABSAClient


class _CfgOpenAI:
    OPENAI_API_KEY = "sk-test-key"
    OPENAI_MODEL = "gpt-4o-mini"


class TestOpenAIBatchJsonl(unittest.TestCase):

    def test_linea_jsonl_custom_id_y_body(self):
        client = OpenAIBatchABSAClient(_CfgOpenAI)
        topicos = [{"id": 1, "slug": "limpieza", "nombre": "Limpieza"}]
        line = client.construir_linea_jsonl(
            99,
            "La habitación estaba impecable.",
            topicos,
            None,
        )
        obj = json.loads(line)
        self.assertEqual(obj["custom_id"], "99")
        self.assertEqual(obj["method"], "POST")
        self.assertEqual(obj["url"], "/v1/chat/completions")
        self.assertEqual(obj["body"]["model"], "gpt-4o-mini")
        self.assertEqual(obj["body"]["temperature"], 0)
        self.assertEqual(obj["body"]["response_format"], {"type": "json_object"})
        self.assertIn("Limpieza", obj["body"]["messages"][0]["content"])


class TestValidatorsSincronizarBatch(unittest.TestCase):

    def test_vacio_ok(self):
        self.assertEqual(validar_body_sincronizar_batch(None), [])
        self.assertEqual(validar_body_sincronizar_batch({}), [])

    def test_openai_batch_id_valido(self):
        self.assertEqual(
            validar_body_sincronizar_batch({"openai_batch_id": "batch_abc"}),
            [],
        )

    def test_openai_batch_id_invalido(self):
        errs = validar_body_sincronizar_batch({"openai_batch_id": ""})
        self.assertTrue(len(errs) > 0)


if __name__ == "__main__":
    unittest.main()
