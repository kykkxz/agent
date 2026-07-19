import math
import threading
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path


RECORD_FILE = Path(__file__).resolve().parent / "exam_records.txt"

student_records: dict[str, dict[str, float]] = {}
record_lock = threading.Lock()


def check_valid_score(score: float, max_score: float) -> bool:
    if max_score <= 0:
        raise ValueError("满分必须大于 0")
    return 0 <= score <= max_score


def calc_percentage(score: float, max_score: float) -> float:
    if not check_valid_score(score, max_score):
        raise ValueError(f"成绩必须在 0 到 {max_score} 之间")
    return score / max_score * 100


def save_record(record_info: str) -> None:
    with RECORD_FILE.open("a", encoding="utf-8") as file:
        _ = file.write(f"{record_info}\n")


def read_all_records() -> list[str]:
    if not RECORD_FILE.exists():
        return []
    with RECORD_FILE.open("r", encoding="utf-8") as file:
        return [line.rstrip("\n") for line in file]


def get_excellent_students(score_dict, threshold: int) -> list[str]:
    return [student for student, score in score_dict.items() if score >= threshold]


def report_card_generator(student_list: Sequence[Mapping[str, object]]) -> Iterator[str]:
    for student in student_list:
        name = student["name"]
        subject = student["subject"]
        score = student["score"]
        grade = student["grade"]
        yield f"学生：{name}，科目：{subject}，成绩：{score}，等级：{grade}"


def input_score_thread_safe(student_name: str, subject: str, score: float):
    with record_lock:
        student_records.setdefault(student_name, {})[subject] = score
        save_record(f"{student_name},{subject},{score}")


def multi_thread_input_test() -> dict[str, dict[str, float]]:
    threads = [
        threading.Thread(target=input_score_thread_safe, args=("1", "语文", 136)),
        threading.Thread(target=input_score_thread_safe, args=("2", "数学", 142)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    with record_lock:
        return {student: scores.copy() for student, scores in student_records.items()}


def calculate_class_ranking(
    records_dict: dict[str, dict[str, float]],
) -> list[tuple[str, float]]:
    totals = [
        (student, sum(subject_scores.values()))
        for student, subject_scores in records_dict.items()
    ]
    return sorted(totals, key=lambda item: item[1], reverse=True)


def check_balance(student_scores: dict[str, float]) -> str:
    if not student_scores:
        raise ValueError("学生成绩不能为空")

    scores = list(student_scores.values())
    average = sum(scores) / len(scores)
    standard_deviation = math.sqrt(
        sum((score - average) ** 2 for score in scores) / len(scores)
    )

    if standard_deviation < 10:
        return f"标准差 {standard_deviation:.2f}：各科均衡"
    if standard_deviation < 20:
        return f"标准差 {standard_deviation:.2f}：轻微偏科"

    weakest_subject = min(student_scores, key=lambda subject: student_scores[subject])
    strongest_subject = max(student_scores, key=lambda subject: student_scores[subject])
    return (
        f"标准差 {standard_deviation:.2f}：严重偏科，"
        f"优势科目：{strongest_subject}，薄弱科目：{weakest_subject}"
    )
