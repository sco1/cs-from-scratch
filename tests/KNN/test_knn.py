import csv

from cs_from_scratch.KNN.digit import Digit
from cs_from_scratch.KNN.fish import Fish
from cs_from_scratch.KNN.knn import KNN
from tests.KNN import TEST_DATA_DIR

FISH_CSV = TEST_DATA_DIR / "fish" / "fish.csv"


def test_nearest() -> None:
    k = 3
    fish_knn = KNN(Fish, FISH_CSV)
    test_fish = Fish("", 0.0, 30.0, 32.5, 38.0, 12.0, 5.0)

    nearest_fish = fish_knn.nearest(k=k, data_point=test_fish)
    assert len(nearest_fish) == k

    expected_fish = [
        Fish("Bream", 340.0, 29.5, 32.0, 37.3, 13.9129, 5.0728),
        Fish("Bream", 500.0, 29.1, 31.5, 36.4, 13.7592, 4.368),
        Fish("Bream", 700.0, 30.4, 33.0, 38.3, 14.8604, 5.2854),
    ]

    assert nearest_fish == expected_fish  # Might need to add a compatible tolerance here


def test_classify() -> None:
    k = 5
    fish_knn = KNN(Fish, FISH_CSV)
    test_fish = Fish("", 0.0, 20.0, 23.5, 24.0, 10.0, 4.0)

    classify_fish = fish_knn.classify(k=k, data_point=test_fish)
    assert classify_fish == "Parkki"


DIGITS_DATA_CSV = TEST_DATA_DIR / "digits" / "digits.csv"
DIGITS_TEST_CSV = TEST_DATA_DIR / "digits" / "digits_test.csv"


def test_digits_test_set() -> None:
    k = 1
    digits_knn = KNN(Digit, DIGITS_DATA_CSV, has_header=False)

    test_data_points: list[Digit] = []
    with DIGITS_TEST_CSV.open("r") as f:
        reader = csv.reader(f)
        for row in reader:
            test_data_points.append(Digit.from_string_data(row))

    correct_classifications = 0
    for point in test_data_points:
        predicted = digits_knn.classify(k=k, data_point=point)
        if predicted == point.kind:
            correct_classifications += 1

    correct_percentage = (correct_classifications / len(test_data_points)) * 100

    print(
        f"Correct Classifications: {correct_classifications} of {len(test_data_points)} ({correct_percentage:0.2f}%)"
    )

    assert correct_percentage > 97.0
