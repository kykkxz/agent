"""
简易学生班级管理小工具：

1. 数据表模型创建（学生表 + 班级表）
2. 批量新增测试数据
3. 条件查询、排序、分页查询
4. 修改、删除数据
5. 事务异常回滚保护
6. 数据统计（平均分、总人数）
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    desc,
    func,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/student_db?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=True)
Base: Any = declarative_base()
SessionLocal: Any = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Class(Base):
    """班级表"""

    __tablename__ = "class_table"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name = Column(String(30), nullable=False, unique=True, comment="班级名")
    teacher = Column(String(20), comment="班主任")
    student_num = Column(Integer, default=0, server_default="0", comment="人数")

    students = relationship(
        "Student",
        back_populates="class_room",
        cascade="all, delete-orphan",
    )


class Student(Base):
    """学生表"""

    __tablename__ = "student_table"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name = Column(String(10), nullable=False, unique=True, comment="学生名")
    score = Column(Float, default=0.0, comment="考试成绩")
    class_id = Column(Integer, ForeignKey("class_table.id"), nullable=False, comment="关联班级ID")

    class_room = relationship("Class", back_populates="students")


def init_db() -> None:
    """初始化数据库建表"""
    Base.metadata.create_all(bind=engine)
    print("数据表创建成功！")


def get_session() -> Any:
    return SessionLocal()


def add_test_data() -> None:
    """批量录入班级与学生测试数据"""
    session = get_session()
    try:
        session.query(Student).delete()
        session.query(Class).delete()

        classes = [
            Class(name="高三(1)班", teacher="张老师"),
            Class(name="高三(2)班", teacher="李老师"),
        ]
        session.add_all(classes)
        session.flush()

        students = [
            Student(name="张三", score=92.5, class_id=classes[0].id),
            Student(name="李四", score=78.0, class_id=classes[0].id),
            Student(name="王五", score=85.5, class_id=classes[0].id),
            Student(name="赵六", score=59.0, class_id=classes[1].id),
            Student(name="钱七", score=96.0, class_id=classes[1].id),
            Student(name="孙八", score=62.0, class_id=classes[1].id),
        ]
        session.add_all(students)

        for class_item in classes:
            class_item.student_num = len(class_item.students) # pyright:ignore

        session.commit()
        print("批量数据初始化成功！")
    except SQLAlchemyError as exc:
        session.rollback()
        print(f"初始化数据失败，错误: {exc}")
    finally:
        session.close()


def print_student(student: Student) -> None:
    print(student.id, student.name, student.score, student.class_room.name)


def query_students() -> None:
    """条件查询、排序、分页查询"""
    session = get_session()
    try:
        print("成绩大于80分的学生：")
        high_score_students = session.query(Student).filter(Student.score > 80).all()
        for student in high_score_students:
            print_student(student)

        print("按成绩倒序：")
        ordered_students = session.query(Student).order_by(desc(Student.score)).all()
        for student in ordered_students:
            print_student(student)

        page = 1
        page_size = 3
        print(f"第{page}页，每页{page_size}条：")
        page_students = (
            session.query(Student)
            .order_by(Student.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        for student in page_students:
            print_student(student)
    finally:
        session.close()


def update_student_score(student_name: str, new_score: float) -> None:
    """修改学生成绩"""
    session = get_session()
    try:
        student = session.query(Student).filter(Student.name == student_name).first()
        if student is None:
            print(f"未找到学生：{student_name}")
            return

        student.score = new_score
        session.commit()
        print(f"{student_name}成绩修改为：{new_score}")
    except SQLAlchemyError as exc:
        session.rollback()
        print(f"修改失败，错误: {exc}")
    finally:
        session.close()


def delete_student(student_name: str) -> None:
    """删除学生数据并同步班级人数"""
    session = get_session()
    try:
        student = session.query(Student).filter(Student.name == student_name).first()
        if student is None:
            print(f"未找到学生：{student_name}")
            return

        class_room = student.class_room
        session.delete(student)
        session.flush()
        class_room.student_num = session.query(Student).filter(Student.class_id == class_room.id).count()
        session.commit()
        print(f"已删除学生：{student_name}")
    except SQLAlchemyError as exc:
        session.rollback()
        print(f"删除失败，错误: {exc}")
    finally:
        session.close()


def demonstrate_transaction_rollback() -> None:
    """事务异常回滚保护"""
    session = get_session()
    try:
        student = session.query(Student).filter(Student.name == "张三").first()
        if student is None:
            raise RuntimeError("张三不存在，无法演示事务回滚")

        old_score = student.score
        student.score = 0
        session.add(Student(name="事务异常学生", score=100.0, class_id=student.class_id))
        raise RuntimeError("模拟异常，触发事务回滚")
    except RuntimeError as exc:
        session.rollback()
        print(f"事务已回滚：{exc}")
        restored_student = session.query(Student).filter(Student.name == "张三").first()
        rolled_back_student = session.query(Student).filter(Student.name == "事务异常学生").first()
        if restored_student is not None:
            print(f"张三成绩仍为：{restored_student.score}")
        print(f"异常学生是否存在：{rolled_back_student is not None}")
        if "old_score" in locals() and restored_student is not None and restored_student.score != old_score: # pyright: ignore
            print("回滚校验失败")
    except SQLAlchemyError as exc:
        session.rollback()
        print(f"事务执行失败，错误: {exc}")
    finally:
        session.close()


def print_statistics() -> None:
    """统计平均分、总人数和班级人数"""
    session = get_session()
    try:
        total_count, average_score = session.query(
            func.count(Student.id),
            func.avg(Student.score),
        ).one()

        print("学生总人数：", total_count)
        print("平均分：", round(float(average_score or 0), 2))

        class_stats = (
            session.query(Class.name, func.count(Student.id), func.avg(Student.score))
            .outerjoin(Student)
            .group_by(Class.id, Class.name)
            .order_by(Class.id)
            .all()
        )
        print("班级统计：")
        for class_name, student_count, average_class_score in class_stats:
            print(class_name, student_count, round(float(average_class_score or 0), 2))
    finally:
        session.close()


def main() -> None:
    init_db()
    add_test_data()
    query_students()
    update_student_score("赵六", 61.0)
    delete_student("孙八")
    demonstrate_transaction_rollback()
    print_statistics()


if __name__ == "__main__":
    main()
