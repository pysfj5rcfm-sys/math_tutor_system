from src.core.student_profile import load_student_profile


def test_student_profile_can_load():
    profile = load_student_profile()
    assert profile["student_id"] == "daughter_grade5"
    assert profile["grade"] == "小学五年级"
