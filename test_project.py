import pytest

from project import calculate_reading_time, count_words, validate_document_name


def test_count_words():
    assert count_words("") == 0
    assert count_words("   ") == 0
    assert count_words("Hello") == 1
    assert count_words("Hello world") == 2
    assert count_words("Hello,   world!") == 2

    # Hyphenated, apostrophe'd, and dotted words count as one word each.
    assert count_words("well-known") == 1
    assert count_words("don't") == 1
    assert count_words("U.S.A.") == 1

    assert count_words("The well-known author didn't stop writing.") == 6

    with pytest.raises(TypeError):
        count_words(123)

    with pytest.raises(TypeError):
        count_words(None)

def test_calculate_reading_time():
    assert calculate_reading_time(0) == 0.0
    assert calculate_reading_time(200) == 1.0
    assert calculate_reading_time(100) == 0.5
    assert calculate_reading_time(100, words_per_minute=100) == 1.0

    with pytest.raises(ValueError):
        calculate_reading_time(-1)

    with pytest.raises(ValueError):
        calculate_reading_time(100, words_per_minute=0)

    with pytest.raises(ValueError):
        calculate_reading_time(100, words_per_minute=-50)

    with pytest.raises(TypeError):
        calculate_reading_time("100")

    with pytest.raises(TypeError):
        calculate_reading_time(100, words_per_minute="fast")



def test_validate_document_name():
    assert validate_document_name("NewDoc1") == "NewDoc1"
    assert validate_document_name("My Essay") == "My Essay"

    with pytest.raises(TypeError):
        validate_document_name(123)

    with pytest.raises(ValueError):
        validate_document_name("")

    with pytest.raises(ValueError):
        validate_document_name("   ")

    with pytest.raises(ValueError):
        validate_document_name(".")

    with pytest.raises(ValueError):
        validate_document_name("..")

    with pytest.raises(ValueError):
        validate_document_name("notes/draft")

    with pytest.raises(ValueError):
        validate_document_name("notes:draft")

    with pytest.raises(ValueError):
        validate_document_name("CON")

    with pytest.raises(ValueError):
        validate_document_name("con")
