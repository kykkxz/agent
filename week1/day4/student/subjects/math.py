from .base_exam import BaseExam


class MathExam(BaseExam):
    def __init__(self, student_name: str):
        super().__init__("数学", 150, student_name)
        self.__bonus_points = 0.0

    def get_bonus_points(self):
        return self.__bonus_points

    def set_bonus_points(self, points : float):
        if points < 0:
            raise ValueError("附加分不能小于 0")
        self.__bonus_points = float(points)

    def get_grade(self, score: float):
        if score >= 140:
            return "优秀"
        if score >= 120:
            return "良好"
        if score >= 90:
            return "及格"
        return "不及格"

    def calc_weighted_score(self, weight: object):
        return super().calc_weighted_score(weight) + self.__bonus_points
