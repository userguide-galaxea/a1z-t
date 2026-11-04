# A1Z-T: A1Z Teleoperation

[English](README_EN.md)

A1Z-T 对 A1Z 的单臂和双臂遥操作。双臂模式使用独立线程控制两侧。

## 安装

需要 Ubuntu 22.04 和 CPython 3.11。

在仓库根目录初始化 submodule：

```bash
git submodule update --init GALAXEA-A1Z
```

选择一种环境安装方式。

### venv

先确认 Python 3.11 已安装并在 `PATH` 中：

```bash
python3.11 --version
```

本项目包含 CPython 3.11 字节码，不能用系统的 Python 3.10 代替。若提示 `command not found: python3.11`，可先按 [uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/) 安装 uv，再让它下载 Python 3.11 并创建带 pip 的环境：

```bash
uv venv --python 3.11 --seed --system-site-packages .venv && \
source .venv/bin/activate
```

已有 Python 3.11 时，也可以直接使用标准库创建环境：

```bash
python3.11 -m venv --system-site-packages .venv && \
source .venv/bin/activate
```

若提示缺少 `venv` 或 `ensurepip`，需安装与 Python 3.11 配套的 venv 组件。通过 apt 安装 Python 3.11 时，通常还需从同一软件源安装 `python3.11-venv`。若软件源没有该包，可使用上面的 uv 方式。

创建成功后才能激活；若创建失败，`.venv/bin/activate` 可能不存在。激活后运行 `python --version`，确认输出为 `Python 3.11.x`。已有其他 Python 版本的 `.venv` 时，先移走旧环境，再重新创建。

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

如果 pip 下载依赖较慢，可改用[清华 PyPI 镜像](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)：

```bash
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

使用 venv 时，也可为当前虚拟环境保存镜像设置，后续安装无需重复添加 `-i`：

```bash
python -m pip config --site set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

镜像只加速 PyPI 包下载。本项目的 `a1z` 依赖仍从 GitHub 获取；若卡在 `git clone`，需要单独检查 GitHub 网络连接。

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

本项目自有内容采用 [Galaxea Dynamics A1Z-T LICENSE AGREEMENT](LICENSES.md)。分发声明见 [NOTICE](NOTICE)。随附组件保留各自许可证，见 [a1z_t/licenses](a1z_t/licenses)。分发字节码时须保留同名 `.pyc.license` 文件。
