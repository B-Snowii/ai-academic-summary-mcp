# Deployment Guide

## Privacy Protection
- `database.json` may contain private data. Ensure it is listed in `.gitignore` and never pushed.
- In public deployments, database features are disabled automatically when `PRIVACY_MODE=true`.

### Local Development
1. Keep `database.json` ignored by Git.
2. Set `PRIVACY_MODE=false` (default).
3. Database features will work locally.

### Public Deployment (GitHub/Hugging Face)
1. Set environment variable `PRIVACY_MODE=true`.
2. Database features will be disabled; the app continues to work.

### Hugging Face Spaces
1. Open your Space settings → Repository secrets
2. Add variable: `PRIVACY_MODE=true`

### Verification Checklist
- `database.json` is in `.gitignore`.
- Only `database_example.json` or `sample.json` is included in the repo.

## Steps
### GitHub
```bash
git add .
git commit -m "Deploy"
git push origin main
```

### Hugging Face Spaces
1. Ensure `database.json` is NOT uploaded
2. Set `PRIVACY_MODE=true`
3. Deploy and verify

## Troubleshooting
- Check `PRIVACY_MODE` value
- Confirm `database.json` is not tracked
- Restart the app

---

# 部署说明（中文）

## 隐私保护
- `database.json` 可能包含隐私数据，请确保已写入 `.gitignore`，不要推送。
- 公共部署中将 `PRIVACY_MODE=true`，数据库功能会自动禁用，但应用可正常使用。

### 本地开发
1. 确保 `database.json` 被 Git 忽略。
2. 设置 `PRIVACY_MODE=false`（默认）。
3. 本地可使用数据库相关功能。

### 公共部署（GitHub/Hugging Face）
1. 设置环境变量 `PRIVACY_MODE=true`。
2. 数据库功能将被禁用，应用仍可正常工作。

### Hugging Face Spaces
1. 打开 Space 设置 → Repository secrets
2. 添加变量：`PRIVACY_MODE=true`

### 验证清单
- `.gitignore` 中包含 `database.json`
- 仓库中仅保留 `database_example.json` 或 `sample.json`

## 部署步骤
### GitHub
```bash
git add .
git commit -m "Deploy"
git push origin main
```

### Hugging Face Spaces
1. 确保不上传 `database.json`
2. 设置 `PRIVACY_MODE=true`
3. 部署并验证

## 故障排除
- 检查 `PRIVACY_MODE` 值
- 确认 `database.json` 未被跟踪
- 重启应用
