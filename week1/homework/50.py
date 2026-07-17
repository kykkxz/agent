'''
题目：有五个学生，每个学生有3门课的成绩，从键盘输入以上数据（包括学生号，姓名，三门课成绩），计算出平均成绩，况原有的数据和计算出的平均分数存放在磁盘文件 "stud "中。
'''

class Student:
    def __init__(self, sid : str, name : str, grades : dict):
        self.id = sid
        self.name = name
        self.grades = grades
        self.avg_score = self.calculate_avg()


    def calculate_avg(self) -> float:
        if not self.grades:
            return 0.0
        return sum(self.grades.values()) / len(self.grades)

    def to_file_line(self) -> str:
        """格式化输出，方便写入文件"""
        grades_str = " ".join([f"{k}:{v}" for k, v in self.grades.items()])
        return f"学号:{self.id} | 姓名:{self.name} | 成绩:({grades_str}) | 平均分:{self.avg_score:.2f}\n"

def stat():
    student_list = []

    for i in range(5):
        sid = input("请输入学生号:\n")
        name = input("请输入名字:\n")
        
        grades = {}
        for course in ["课程1", "课程2", "课程3"]:
            score = float(input(f"请输入 {course} 的成绩: "))
            grades[course] = score

        stu = Student(sid, name, grades)
        student_list.append(stu)
        
            
    with open("stud", "w", encoding="utf-8") as f:
        for stu in student_list:
            f.write(stu.to_file_line())

    print("所有学生数据已保存至磁盘文件 'stud' 中")

if __name__ == "__main__":
    stat()
