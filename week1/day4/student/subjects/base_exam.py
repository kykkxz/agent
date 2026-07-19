from abc import ABC, abstractmethod

from grade_utils import check_valid_score


class BaseExam(ABC):
    passing_rate: float = 0.6

    def __init__(self, subject_name: str, max_score, student_name) -> None:
        if not self.check_student_name(student_name):
            raise ValueError("学生姓名不能为空")
        if max_score <= 0:
            raise ValueError("满分必须大于 0")

        self.subject_name: str = subject_name
        self.max_score: float = float(max_score)
        self.student_name: str = student_name
        self.__score = 0.0

    def get_score(self):
        return self.__score

    def input_score(self, score: float):
        if not check_valid_score(score, self.max_score):
            raise ValueError(f"{self.subject_name}成绩必须在 0 到 {self.max_score} 之间")
        self.__score = float(score)

    @classmethod
    def set_passing_rate(cls, rate: float) :
        if not 0 < rate <= 1:
            raise ValueError("及格率必须在 0 到 1 之间")
        cls.passing_rate = float(rate)

    @staticmethod
    def check_student_name(name):
        return isinstance(name, str) and bool(name.strip())

    @abstractmethod
    def get_grade(self, score: float):
        raise NotImplementedError

    def calc_weighted_score(self, weight):
        if weight < 0:
            raise ValueError("权重不能小于 0")
        return self.get_score() * float(weight)

    def print_report_card(self):
        score = self.get_score()
        grade = self.get_grade(score)
        print(f"成绩单：{self.student_name} | {self.subject_name} | {score:.1f}分 | {grade}")

    def compare_with_previous(self, previous_score: float):
        if not check_valid_score(previous_score, self.max_score):
            raise ValueError(f"上次成绩必须在 0 到 {self.max_score} 之间")

        current_score = self.get_score()
        difference = current_score - previous_score
        percent = difference / previous_score * 100 if previous_score else 0
        direction = "进步" if difference >= 0 else "退步"
        previous_grade = self.get_grade(previous_score)
        current_grade = self.get_grade(current_score)
        grade_change = (
            f"等级由{previous_grade}变为{current_grade}"
            if previous_grade != current_grade
            else f"等级保持{current_grade}"
        )

        return f"{direction}{abs(difference):.1f}分，变化{abs(percent):.2f}%，{grade_change}"
