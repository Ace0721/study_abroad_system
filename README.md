# 留学申请与审核软件（课程作业）

本项目是一个基于 `PySide6 + SQLite + SQLAlchemy` 的 Windows 桌面端课程作业示例。

## 当前阶段

当前代码为阶段 6 的最小可运行骨架：

- 可启动程序并打开登录窗口
- 可初始化数据库并写入种子数据
- 已预置 6 个角色账号
- 界面结构采用“登录窗口 + 角色主窗口 + Tab 页”
- 每个业务按钮都预留了唯一 service 动作入口

## 启动方式

1. 安装依赖：
   - `pip install -r requirements.txt`
2. 运行：
   - `python main.py`

## 初始化演示数据（阶段8）

1. 基础账号/学校/专业数据：
   - 已在启动时自动执行
2. 10~20 条演示申请数据：
   - `python database/seed_demo_data.py`
3. 手工场景脚本（6个核心场景）：
   - `python tests/manual_test_script.py`

## 预置账号（初始密码统一为 123456）

- `anu_officer`
- `usyd_officer`
- `unsw_officer`
- `agent_a`
- `agent_b`
- `reviewer`
