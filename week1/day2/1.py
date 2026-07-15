class Pet:
    def __init__(self, name, species, energy = 100):
        self.name = name
        self.species = species
        self.energy = energy

    def play(self):
        self.energy -= 20
        if self.energy > 0:
            print(f"{self.name}玩得很开心，剩余精力{self.energy}")
            return None
        print(f"XX累坏了，玩不动了") 

    def eat(self):
        self.energy += 30
        if self.energy >= 100:
            self.energy = 100
        print(f"{self.name}吃饱了，精力恢复到{self.energy}")

print("--- 场景测试：猫 ---")

cat = Pet("1", "猫", 100)
cat.eat()
cat.play()

class WorkingDog(Pet):
    def __init__(self, name, job, energy=100):
        super().__init__(name, "狗", energy)
        self.job = job

    def work(self):
        if self.energy >= 40:
            self.energy -= 40
            print(f"{self.name}({self.job})执行任务，剩余精力{self.energy}")
        else:
            print(f"{self.name}精力不足，无法执行任务")

    def play(self):
        print(f"{self.name}虽然是工作犬，但也要放松一下")
        super().play()

print("--- 场景测试：工作犬 ---")

dog = WorkingDog("2", "导盲")

dog.work()

dog.play()

dog.eat()



