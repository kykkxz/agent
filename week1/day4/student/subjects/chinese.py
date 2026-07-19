from .base_exam import BaseExam


class ChineseExam(BaseExam):
    def __init__(self, student_name: str, essay_score : float) :
        super().__init__("语文", 150, student_name)

        if not 0 <= essay_score <= 60:
            raise ValueError("作文分必须在 0 到 60 之间")
        self.essay_score: float = float(essay_score)

    def get_grade(self, score: float):
        if score >= 135:
            return "优秀"
        if score >= 120:
            return "良好"
        if score >= 90:
            return "及格"
        return "不及格"
