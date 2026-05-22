from sklearn.metrics import precision_recall_fscore_support


CATEGORY_MAPPING = {
    'service general':          'Atención del personal',
    'hotel cleanliness':        'Limpieza',
    'rooms cleanliness':        'Limpieza',
    'location general':         'Ubicación',
    'hotel general':            'Instalaciones y servicios',
    'hotel quality':            'Instalaciones y servicios',
    'hotel design_features':    'Instalaciones y servicios',
    'hotel miscellaneous':      'Instalaciones y servicios',
    'facilities general':       'Instalaciones y servicios',
    'facilities design_features': 'Instalaciones y servicios',
    'room_amenities general':   'Instalaciones y servicios',
    'room_amenities quality':   'Instalaciones y servicios',
    'food_drinks quality':      'Alimentación',
    'food_drinks prices':       'Alimentación',
    'rooms general':            'Confort de la habitación',
    'rooms comfort':            'Confort de la habitación',
    'rooms design_features':    'Confort de la habitación',
    'rooms quality':            'Confort de la habitación',
    'hotel comfort':            'Confort de la habitación',
    'room_amenities comfort':   'Confort de la habitación',
    'hotel prices':             'Relación calidad-precio',
}

CATEGORIES = [
    'Atención del personal',
    'Limpieza',
    'Ubicación',
    'Instalaciones y servicios',
    'Alimentación',
    'Confort de la habitación',
    'Relación calidad-precio',
]

POLARITIES = ['positive', 'negative', 'neutral']


def map_category(raw_category):
    return CATEGORY_MAPPING.get(raw_category.lower().strip())


def compute_absa_metrics(predictions, ground_truth):
    """
    predictions: list of sets, cada set contiene tuplas (category, polarity)
    ground_truth: list of sets, misma estructura
    Retorna dict con precision, recall, f1_micro, f1_macro por categoría.
    """
    all_labels = set()
    for gt in ground_truth:
        all_labels.update(gt)
    for pred in predictions:
        all_labels.update(pred)

    label_list = sorted(all_labels)
    label_idx = {l: i for i, l in enumerate(label_list)}

    y_true = []
    y_pred = []

    for gt, pred in zip(ground_truth, predictions):
        for label in label_list:
            y_true.append(1 if label in gt else 0)
            y_pred.append(1 if label in pred else 0)

    p_micro, r_micro, f1_micro, _ = precision_recall_fscore_support(
        y_true, y_pred, average='micro', zero_division=0
    )
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average='macro', zero_division=0
    )

    return {
        'precision_micro': p_micro,
        'recall_micro': r_micro,
        'f1_micro': f1_micro,
        'precision_macro': p_macro,
        'recall_macro': r_macro,
        'f1_macro': f1_macro,
    }
