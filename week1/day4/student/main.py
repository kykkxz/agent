from grade_utils import *
from subjects import BaseExam, ChineseExam, EnglishExam, MathExam


def test_percentage():
    percentage = calc_percentage(135, 150)
    print(f"135/150 得分率：{percentage:.2f}%")


def test_save_and_read():
    save_record("测试学生,语文,128")
    save_record("测试学生,数学,139")
    records = read_all_records()
    print("最近 3 条成绩记录：")
    for record in records[-3:]:
        print(record)


def test_multi_thread_input():
    result = multi_thread_input_test()
    print(f"并发录入结果：{result}")


def test_passing_rate():
    BaseExam.set_passing_rate(0.65)
    print(f"当前及格率：{BaseExam.passing_rate:.0%}")


def create_subject_samples():
    chinese_exam = ChineseExam("5", essay_score=52)
    chinese_exam.input_score(138)

    math_exam = MathExam("6")
    math_exam.input_score(145)
    math_exam.set_bonus_points(5)

    english_exam = EnglishExam("7")
    english_exam.input_score(92)

    return chinese_exam, math_exam, english_exam


def test_chinese(chinese_exam: ChineseExam) -> None:
    print(f"作文分：{chinese_exam.essay_score:.1f}")
    score = chinese_exam.get_score()
    grade = chinese_exam.get_grade(score)
    print(f"等级：{grade}")
    print(chinese_exam.compare_with_previous(126))
    save_record(f"{chinese_exam.student_name},{chinese_exam.subject_name},{score:.1f},{grade}")


def test_math(math_exam: MathExam):
    print(f"附加分：{math_exam.get_bonus_points():.1f}")
    print(f"期末 70% 加权分：{math_exam.calc_weighted_score(0.7):.1f}")
    score = math_exam.get_score()
    grade = math_exam.get_grade(score)
    print(f"等级：{grade}")
    save_record(f"{math_exam.student_name},{math_exam.subject_name},{score:.1f},{grade}")


def test_english(english_exam: EnglishExam):
    english_exam.print_report_card()
    score = english_exam.get_score()
    grade = english_exam.get_grade(score)
    print(f"等级：{grade}")
    save_record(f"{english_exam.student_name},{english_exam.subject_name},{score:.1f},{grade}")


def test_excellent_students():
    scores = {"11": 138, "12": 145, "122": 92, "321": 88}
    excellent_students = get_excellent_students(scores, 135)
    print(f"优秀学生：{excellent_students}")


def test_report_card_generator(chinese_exam, math_exam, english_exam):
    student_list = [
        {
            "name": exam.student_name,
            "subject": exam.subject_name,
            "score": exam.get_score(),
            "grade": exam.get_grade(exam.get_score()),
        }
        for exam in (chinese_exam, math_exam, english_exam)
    ]
    for report_card in report_card_generator(student_list):
        print(report_card)


def test_polymorphic_statistics(chinese_exam, math_exam, english_exam):
    exams = [chinese_exam, math_exam, english_exam]
    weighted_scores = [round(exam.calc_weighted_score(0.7), 1) for exam in exams]
    total_score = sum(exam.get_score() for exam in exams)
    average_score = total_score / len(exams)
    print(f"三科总分：{total_score:.1f}")
    print(f"三科平均分：{average_score:.1f}")
    print(f"多态加权分：{weighted_scores}")


def test_extra_challenges():
    input_score_thread_safe("a", "语文", 138)
    input_score_thread_safe("b", "数学", 132)
    input_score_thread_safe("c", "英语", 92)
    input_score_thread_safe("d", "语文", 121)
    input_score_thread_safe("e", "数学", 145)
    input_score_thread_safe("f", "英语", 84)
    print(f"班级排名：{calculate_class_ranking(student_records)}")
    print(check_balance({"语文": 138, "数学": 132, "英语": 92}))


def main() -> None:
    chinese_exam, math_exam, english_exam = create_subject_samples()

    print("1. 基础得分率计算测试")
    test_percentage()

    print("2. 成绩保存与读取测试")
    test_save_and_read()

    print("3. 多线程录入测试")
    test_multi_thread_input()

    print("4. 设置及格率为 0.65") 
    test_passing_rate()
    
    print("5. 语文测试")
    test_chinese(chinese_exam)

    print("6. 数学测试")
    test_math(math_exam)

    print("7. 英语测试")
    test_english(english_exam)
    
    print("8. 优秀学生筛选测试")
    test_excellent_students()

    print("9. 成绩单生成器测试")
    test_report_card_generator(chinese_exam, math_exam, english_exam)
    
    print("10. 批量统计多态测试")
    test_polymorphic_statistics(chinese_exam, math_exam, english_exam)
    
    print("进阶挑战测试")
    test_extra_challenges()


if __name__ == "__main__":
    main()
