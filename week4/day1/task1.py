import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

# 1. 生成数据
X = torch.randn(1000, 2)
Y = (2 * X[:, 0] - 2 * X[:, 1] + 0.1 * torch.randn(1000)).unsqueeze(1)

# 2. 数据加载
dataset = TensorDataset(X, Y)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# 3. 构建模型
class LinearRegression(nn.Module):
    def __init__(self):
        super().__init__()
        self.liner = nn.Linear(in_features=2, out_features=1)

    def forward(self, x):
        return self.liner(x)

model = LinearRegression()


# 4. 训练配置与循环
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
criterion = nn.MSELoss()

for epoch in range(20):
    total_loss = 0.0
    for batch_X, batch_Y in dataloader:
        # 前向传播
        prediction = model(batch_X)

        # 计算损失
        loss = criterion(prediction, batch_Y)

        # 反向传播
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
    average_loss = total_loss / len(dataloader)
    print(f"Epoch {epoch + 1:02d}, Loss: {average_loss:.4f}")

# 检查学习到的参数
print(model.state_dict())
