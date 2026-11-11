# A1Z-T: A1Z Teleoperation

[English](README_EN.md)

A1Z-T 对 A1Z 的单臂和双臂遥操作。双臂模式使用独立线程控制两侧。

## 安装

需要 Ubuntu 22.04 和 CPython 3.11。

`galaxea_a1z` 是独立的 SDK 仓库，需在仓库根目录单独 clone（该目录已加入 `.gitignore`）：

```bash
git clone --branch main https://github.com/userguide-galaxea/galaxea_a1z.git galaxea_a1z
```

它跟随上游 `main` 分支，本仓库测试过的 commit 为 `156af498a947a830ca38efff4dd08fd2da96a200`。更新用 `git -C galaxea_a1z pull --ff-only`；新版出现异常时可用 `git -C galaxea_a1z checkout 156af498a947a830ca38efff4dd08fd2da96a200` 退回。

不 clone SDK 时，也可以 `python -m pip install -e '.[sdk]'` 从 GitHub 安装测试版本的 `a1z`，代价是无法跟随 `main` 更新。

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

激活所选环境后，在仓库根目录依次安装 SDK 与项目：

```bash
python -m pip install -e ./galaxea_a1z
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

镜像只加速 PyPI 包下载；`galaxea_a1z` 由本地 clone 以可编辑模式安装，不走 pip 索引。

## 设备设置

下面的命令均在仓库根目录执行。单臂可以不绑定端口，直接使用实际设备名；双臂推荐绑定，避免重插或重启后左右设备的编号交换。

### 单臂：不绑定端口

连接一套 Leader 和 Follower，查看实际串口和 CAN 接口：

```bash
ls /dev/ttyACM*
ip -br link
```

例如设备为 `/dev/ttyACM0` 和 `can0`，先配置 CAN，再启动：

```bash
bash scripts/setup_can.sh can0
python teleop_single.py --port /dev/ttyACM0 --can can0
```

如果实际名称不同，请替换命令中的名称。重插或重启后需重新确认编号，并再次配置 CAN。如果尚未出现 CAN 接口，`setup_can.sh can0` 会尝试加载适配器驱动并等待接口出现；仍失败时，按脚本报错检查适配器连接。

### 绑定固定名称：单臂 / 双臂

绑定按适配器的 USB 序列号识别设备，不依赖 USB 插口或临时编号。单臂绑定后使用 `/dev/leader_left` 和 `can_left`；双臂再增加 `/dev/leader_right` 和 `can_right`。

1. **确认每侧适配器的序列号。** 单臂只连接这一套设备；双臂可先只连接左侧，记录后拔下，再只连接右侧并记录。每次运行：

```bash
bash scripts/setup_ports.sh --list
```

输出中的 `Leader candidate` 是 Leader 串口适配器，`CAN candidate` 是 Follower CAN 适配器，`serial=` 后面才是需要填写的值。不要填写 `/dev/ttyACM0` 或 `can0`。若只看到 Leader，先用 `bash scripts/setup_can.sh can0` 初始化当前 CAN 适配器，再重新列出；接口已存在且名称不同时，将 `can0` 换为实际名称。列表中的 CAN 适配器需使用 `gs_usb` 驱动。

2. **写入绑定规则。** 将下面的占位值替换成刚记录的序列号。脚本会调用 `sudo` 安装系统规则，可能要求输入密码。

单臂只传左侧两项：

```bash
LEADER_LEFT_SERIAL=LEFT_LEADER_SERIAL \
CAN_LEFT_SERIAL=LEFT_CAN_SERIAL \
bash scripts/setup_ports.sh
```

双臂一次传齐四项，左右同类适配器的序列号必须不同：

```bash
LEADER_LEFT_SERIAL=LEFT_LEADER_SERIAL \
CAN_LEFT_SERIAL=LEFT_CAN_SERIAL \
LEADER_RIGHT_SERIAL=RIGHT_LEADER_SERIAL \
CAN_RIGHT_SERIAL=RIGHT_CAN_SERIAL \
bash scripts/setup_ports.sh
```

3. **重新插拔适配器或重启，验证固定名称。** 单臂检查：

```bash
ls -l /dev/leader_left
ip -br link show can_left
```

双臂还需检查：

```bash
ls -l /dev/leader_right
ip -br link show can_right
```

确认串口链接存在、CAN 接口名称正确后，单臂只运行第一条，双臂两条都运行：

```bash
bash scripts/setup_can.sh can_left
bash scripts/setup_can.sh can_right
```

绑定规则通常只需安装一次；每次重启或重新插拔 CAN 适配器后，仍需运行相应的 `setup_can.sh`。单臂请显式传入接口名，不带参数的脚本会等待两路 CAN。

运行前，在 [`config.yaml`](config.yaml) 中通过 `a1z_t_version` 选择 `EVT` 或 `PVT`。未绑定的单臂用户使用上面的实际设备名；下文示例使用绑定后的名称。

## 遥操体验

```bash
python teleop_single.py --port /dev/leader_left --can can_left

python teleop_dual.py --port /dev/leader_left --port_right /dev/leader_right \
  --can_left can_left --can_right can_right
```

启动回零完成后，按控制按钮开始或停止跟随；按 `Ctrl+C` 退出。各入口可用 `--help` 查看参数。双臂模式默认不绑核；需要绑核时，先按当前电脑的 CPU 分配选择合适的核心，再使用 `--cpu-bind`。启用遥操作前，请确认设备归属、运动方向及活动空间。

## 设备检查

未绑定端口时，将下面的 `/dev/leader_left` 换成实际串口名，例如 `/dev/ttyACM0`。

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
