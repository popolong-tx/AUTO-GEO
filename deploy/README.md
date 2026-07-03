# BYDGEO 远端服务脚本说明

适用环境：
- 远端主机：`161.118.209.68`
- 用户名：`ubuntu`
- 部署目录：`~/GEOSYS/bydgeo`

## 脚本列表

### 1. 启动
```bash
~/GEOSYS/bydgeo/scripts/start_bydgeo.sh
```
作用：
- 启动后端（8000）
- 启动前端（5173）
- 自动等待服务就绪

### 2. 停止
```bash
~/GEOSYS/bydgeo/scripts/stop_bydgeo.sh
```
作用：
- 停止 BYDGEO 后端和前端
- 清理 PID 文件
- 兜底清理 8000 / 5173 监听进程

### 3. 重启
```bash
~/GEOSYS/bydgeo/scripts/restart_bydgeo.sh
```
作用：
- 先停止
- 再启动
- 适合更新代码后快速重载

## 运行地址

- 后端健康检查：`http://127.0.0.1:8000/health`
- 前端页面：`http://127.0.0.1:5173/`

## 注意事项

- 远端前端脚本使用 `0.0.0.0` 监听，方便对外访问。
- 如果 5173 被其他进程占用，脚本会先清理旧进程再启动。
- 若需要更换端口，请同时修改：
  - `scripts/start_bydgeo.sh`
  - `scripts/stop_bydgeo.sh`

## 文件位置

脚本位于：
- `~/GEOSYS/bydgeo/scripts/start_bydgeo.sh`
- `~/GEOSYS/bydgeo/scripts/stop_bydgeo.sh`
- `~/GEOSYS/bydgeo/scripts/restart_bydgeo.sh`
