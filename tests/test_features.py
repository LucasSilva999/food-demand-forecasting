from src.generate_data import make_dataset
from src.features import FEATURES, TARGET

def test_dataset_is_reproducible_and_has_expected_columns():
    first = make_dataset(rows=48, seed=7)
    second = make_dataset(rows=48, seed=7)
    assert first.equals(second)
    assert set(FEATURES + [TARGET]).issubset(first.columns)
    assert (first[TARGET] >= 0).all()
