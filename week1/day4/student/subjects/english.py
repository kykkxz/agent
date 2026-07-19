from .base_exam import BaseExam


class EnglishExam(BaseExam):
    def __init__(self, student_name: str):
        super().__init__("英语", 100, student_name)

    def get_grade(self, score: float):
        if score >= 90:
            return "优秀"
        if score >= 75:
            return "良好"
        if score >= 60:
            return "及格"
        return "不及格"

    def print_report_card(self):
        print("听力/阅读/写作分项成绩")
        super().print_report_card()
