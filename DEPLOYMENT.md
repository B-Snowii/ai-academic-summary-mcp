# 部署说明

## 隐私保护

### 重要提醒
- `database.json` 文件包含私人对话和敏感信息
- 该文件已被添加到 `.gitignore` 中，不会被上传到Git仓库
- 在公共部署中，数据库功能将被自动禁用

### 本地开发
1. 确保 `database.json` 在 `.gitignore` 中
2. 设置环境变量 `PRIVACY_MODE=false`（默认值）
3. 数据库功能将正常工作

### 公共部署（GitHub/Hugging Face）
1. 设置环境变量 `PRIVACY_MODE=true`
2. 数据库功能将被禁用，应用仍可正常使用
3. 私人数据不会被暴露

### Hugging Face Spaces 环境变量设置
1. 进入你的Space设置页面
2. 点击 "Repository secrets"
3. 添加环境变量：
   - 名称：`PRIVACY_MODE`
   - 值：`true`

### 验证隐私保护
- 检查 `database.json` 是否在 `.gitignore` 中
- 确认 `database_example.json` 是唯一被包含的数据库文件
- 在公共部署中，应用会显示"数据库功能已禁用"的提示

## 部署步骤

### GitHub
```bash
git add .
git commit -m "Add privacy protection"
git push origin main
```

### Hugging Face Spaces
1. 上传文件时确保不包含 `database.json`
2. 在Space设置中设置 `PRIVACY_MODE=true`
3. 部署完成后验证功能正常

## 故障排除

如果遇到数据库相关错误：
1. 检查 `PRIVACY_MODE` 环境变量设置
2. 确认 `database.json` 不在版本控制中
3. 重启应用
