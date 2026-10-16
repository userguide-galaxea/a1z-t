# A1Z-T: A1Z Teleoperation

[English](README_EN.md)

A1Z-T 对 A1Z 的单臂和双臂遥操作。双臂模式使用独立线程控制两侧。

## 安装

需要 Ubuntu 22.04 和 CPython 3.11。

`GALAXEA-A1Z` 固定到提交 `156af498a947a830ca38efff4dd08fd2da96a200`，发布版同样保留此 GitHub 引用；`pip install` 会从同一提交安装 `a1z`。

在仓库根目录初始化 submodule：

```bash
git submodule update --init GALAXEA-A1Z
```

选择一种环境安装方式。

### venv

```bash
python3.11 -m venv --system-site-packages .venv
source .venv/bin/activate
```

### Conda

需要先安装 Conda。

```bash
conda create -n a1z-teleop python=3.11 -y
conda activate a1z-teleop
```

激活所选环境后，在仓库根目录安装项目：

```bash
python -m pip install -e .
```

## 设备设置

先确认左右臂对应的串口和 CAN 接口。若需要固定设备名称，先列出已连接适配器的序列号，再运行绑定脚本：

```bash
bash scripts/setup_ports.sh --list
LEADER_LEFT_SERIAL=... CAN_LEFT_SERIAL=... bash scripts/setup_ports.sh
```

双臂模式还需设置 `LEADER_RIGHT_SERIAL` 和 `CAN_RIGHT_SERIAL`。安装规则后，重新插拔适配器或重启。单臂只需运行下面第一条命令，双臂则两条都运行：

```bash
bash scripts/setup_can.sh can_left
bash scripts/setup_can.sh can_right
```

运行前，在 [`config.yaml`](config.yaml) 中通过 `a1z_t_version` 选择 `EVT` 或 `PVT`。

## 遥操体验

```bash
python teleop_single.py --port /dev/leader_left --can can_left

python teleop_dual.py --port /dev/leader_left --port_right /dev/leader_right \
  --can_left can_left --can_right can_right
```

启动回零完成后，按控制按钮开始或停止跟随；按 `Ctrl+C` 退出。各入口可用 `--help` 查看参数。双臂模式默认不绑核；需要绑核时，先按当前电脑的 CPU 分配选择合适的核心，再使用 `--cpu-bind`。启用遥操作前，请确认设备归属、运动方向及活动空间。

## 设备检查

**`scan_servos.py`：扫描串口设备。** 默认以 1 Mbps 探测指定串口，列出响应设备的 ID、型号编号和通信速率，便于核对端口与设备连接。默认扫描有漏检时，可添加 `--full` 逐个 ID 探测。此工具只发送查询命令，不执行回零或运动。

```bash
python tools/scan_servos.py --port /dev/leader_left
python tools/scan_servos.py --port /dev/leader_left --full
```

**`a1z_t_test.py`：检查 A1Z-T 本体。** 实时显示关节位置、扳机位置、温度、电流、电压及电流峰值，默认还显示控制按钮状态。支持单臂和双臂。启动时会驱动 A1Z-T 回零并保持；按控制按钮或回车后释放并开始监测，监测中可再次按键回零或释放。此工具不控制 A1Z，请在运行前清空 A1Z-T 的活动空间。

```bash
python tools/a1z_t_test.py --port /dev/leader_left
python tools/a1z_t_test.py --dual --port /dev/leader_left --port-right /dev/leader_right
```

## 许可证

本项目自有内容采用 [Galaxea Dynamics A1Z-T LICENSE AGREEMENT](LICENSES.md)。分发声明见 [NOTICE](NOTICE)。随附组件保留各自许可证，见 [a1z_t/licenses](a1z_t/licenses)。分发字节码时须保留同名 `.pyc.license` 文件。A1Z SDK 通过 GitHub submodule 和固定提交的 pip 依赖提供，不包含在本项目的字节码中。
