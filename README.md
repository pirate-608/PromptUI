# PromptUI
一个可视化的AI漫画提示词生成器（An visualized AI comic generator）
### 1. 项目结构（极简版）

```
promptui/
├── app/    
|   ├──main.py             # FastAPI主应用
|   ├──core/
│   ├── analyzer.py        # 文本分析器封装
│   ├── generators.py      # 提示词生成器
│   └── visual_mapper.py   # 视觉映射
├── static/
|   ├── uploads/           # 文件上传位置
|   ├── favicon/           # 网站图标
│   ├── style.css          # 样式
│   └── script.js          # 前端逻辑
├── templates/ 
|   ├── index.html         # 单页UI            # (可选) Jinja2模板
├── c_modules/             # C语言文本分析算法 
├── requirements.txt       # 依赖
└── build.spec            # PyInstaller打包配置
```