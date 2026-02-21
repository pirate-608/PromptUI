let currentAnalysis = null;

// DOM 元素
const inputText = document.getElementById('inputText');
const generateBtn = document.getElementById('generateBtn');
const loadFileBtn = document.getElementById('loadFileBtn');
const fileInput = document.getElementById('fileInput');
const clearBtn = document.getElementById('clearBtn');
const copyBtn = document.getElementById('copyBtn');
const saveBtn = document.getElementById('saveBtn');
const outputSection = document.getElementById('outputSection');
const analysisSection = document.getElementById('analysisSection');
const promptOutput = document.getElementById('promptOutput');
const analysisContent = document.getElementById('analysisContent');
const charCount = document.getElementById('charCount');

// 页面加载时读取配置
document.addEventListener('DOMContentLoaded', () => {
    loadLLMConfig();
    toggleLLMSettings(); // 初始化显示状态
    // 修复：切换模式时自动显示/隐藏 LLM 配置输入框
    document.getElementById('modeSelect').addEventListener('change', toggleLLMSettings);
});

function toggleLLMSettings() {
    const mode = document.getElementById('modeSelect').value;
    const settings = document.getElementById('llmSettings');
    if (mode === 'llm' || mode === 'hybrid') {
        settings.style.display = 'block';
    } else {
        settings.style.display = 'none';
    }
}

function saveLLMConfig() {
    localStorage.setItem('promptui_api_base', document.getElementById('llmApiBase').value);
    localStorage.setItem('promptui_api_key', document.getElementById('llmApiKey').value);
    localStorage.setItem('promptui_model', document.getElementById('llmModel').value);
    alert('配置已保存');
}

function loadLLMConfig() {
    const base = localStorage.getItem('promptui_api_base');
    const key = localStorage.getItem('promptui_api_key');
    const model = localStorage.getItem('promptui_model');

    if (base) document.getElementById('llmApiBase').value = base;
    if (key) document.getElementById('llmApiKey').value = key;
    if (model) document.getElementById('llmModel').value = model;
}

// 动态加载风格选项
fetch('/api/styles')
    .then(response => response.json())
    .then(data => {
        const styleSelect = document.getElementById('styleSelect');
        styleSelect.innerHTML = '';
        (data.styles || []).forEach(style => {
            const opt = document.createElement('option');
            opt.value = style;
            opt.textContent = style;
            styleSelect.appendChild(opt);
        });
    })
    .catch(() => {
        // 失败时兜底
        const styleSelect = document.getElementById('styleSelect');
        styleSelect.innerHTML = '';
        ['清新简洁', '鲜艳活泼', '黑白线稿', '复古风格', '日系动漫'].forEach(style => {
            const opt = document.createElement('option');
            opt.value = style;
            opt.textContent = style;
            styleSelect.appendChild(opt);
        });
    });

// 语言选择初始化（如需后续使用，可通过 document.getElementById('langSelect').value 获取）
document.addEventListener('DOMContentLoaded', () => {
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
        // 可在生成逻辑中读取 langSelect.value 作为目标语言
    }
});
// 前端逻辑
// URL导入逻辑
document.addEventListener('DOMContentLoaded', () => {
    const importUrlBtn = document.getElementById('importUrlBtn');
    if (importUrlBtn) {
        importUrlBtn.addEventListener('click', async () => {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) { alert('请输入有效URL'); return; }
            importUrlBtn.disabled = true;
            importUrlBtn.textContent = '导入中...';
            try {
                const resp = await fetch('/api/fetch_url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await resp.json();
                if (data.success && data.text) {
                    document.getElementById('inputText').value = data.text;
                } else {
                    alert('网页内容获取失败: ' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('请求失败: ' + e);
            }
            importUrlBtn.disabled = false;
            importUrlBtn.textContent = '🌐 导入URL';
        });
    }
});

// 实时统计
inputText.addEventListener('input', () => {
    const text = inputText.value;
    charCount.textContent = text.length;

    // 防抖分析
    clearTimeout(window.analyzeTimer);
    window.analyzeTimer = setTimeout(() => analyzeText(text), 500);
});

// 分析文本
async function analyzeText(text) {
    if (text.length < 10) return;

    const formData = new FormData();
    formData.append('text', text);

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            currentAnalysis = await response.json();
            displayAnalysis(currentAnalysis);
        }
    } catch (error) {
        console.error('分析失败:', error);
    }
}

// 显示分析结果
function displayAnalysis(analysis) {
    analysisSection.style.display = 'block';

    let html = `
        <div class="analysis-stats">
            <p>📊 总字符: ${analysis.total_chars || 0}</p>
            <p>🔤 英文词: ${analysis.en_words || 0}</p>
            <p>🀄️ 中文字: ${analysis.cn_chars || 0}</p>
            <p>📑 章节数: ${analysis.section_count || 0}</p>
            <p>📈 丰富度: ${analysis.richness?.toFixed(2) || 0}</p>
        </div>
    `;

    if (analysis.top_words?.length) {
        html += '<h3>🔑 高频词</h3><ul>';
        analysis.top_words.slice(0, 5).forEach(w => {
            html += `<li>${w.word}: ${w.freq}次</li>`;
        });
        html += '</ul>';
    }

    if (analysis.sensitive_words?.length) {
        html += `<p>⚠️ 敏感词: ${analysis.sensitive_words.join('、')}</p>`;
    }

    analysisContent.innerHTML = html;
}

// 生成提示词
async function generatePrompt() {
    const text = inputText.value.trim();
    if (!text) {
        alert('请输入文本');
        return;
    }

    // 显示加载状态
    generateBtn.classList.add('loading');
    generateBtn.textContent = '生成中...';

    try {
        // --- 修改开始：构造包含 LLM 配置的请求体 ---
        const requestBody = {
            text: text,
            mode: document.getElementById('modeSelect').value,
            panels: parseInt(document.getElementById('panelsInput').value),
            style: document.getElementById('styleSelect').value,
            sensitive_filter: document.getElementById('sensitiveFilter').checked,
            llm_api_base: document.getElementById('llmApiBase').value,
            llm_api_key: document.getElementById('llmApiKey').value,
            llm_model: document.getElementById('llmModel').value,
            language: document.getElementById('langSelect').value // 新增语言字段
        };
        // --- 修改结束 ---

        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody) // 使用新的 requestBody
        });

        const result = await response.json();

        if (result.success) {
            promptOutput.textContent = result.prompt;
            outputSection.style.display = 'block';

            // 滚动到结果
            outputSection.scrollIntoView({ behavior: 'smooth' });

            // 可选优化：生成成功后自动保存一下配置（防止用户忘记点保存）
            if (typeof saveLLMConfig === 'function') {
                saveLLMConfig();
            }
        } else {
            alert('生成失败: ' + result.error);
        }
    } catch (error) {
        alert('请求失败: ' + error.message);
    } finally {
        generateBtn.classList.remove('loading');
        generateBtn.textContent = '🎨 生成提示词';
    }
}

// 加载文件
loadFileBtn.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        inputText.value = result.content;
        charCount.textContent = result.content.length;
    } catch (error) {
        alert('文件读取失败: ' + error.message);
    }
});

// 清空
clearBtn.addEventListener('click', () => {
    inputText.value = '';
    charCount.textContent = '0';
    outputSection.style.display = 'none';
    analysisSection.style.display = 'none';
});

// 复制
copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(promptOutput.textContent)
        .then(() => alert('已复制到剪贴板'))
        .catch(() => alert('复制失败'));
});

// 保存
saveBtn.addEventListener('click', () => {
    const content = promptOutput.textContent;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prompt_${new Date().getTime()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

// 生成按钮点击
generateBtn.addEventListener('click', generatePrompt);

// 初始化
(async function () {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        console.log('系统状态:', stats);
    } catch (error) {
        console.error('无法连接服务器');
    }
})();