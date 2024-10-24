function applyFontsToText() {
    var bilingualContent = document.querySelectorAll(".bilingual-text");
    bilingualContent.forEach(function (element) {
        // 为中文文本添加中文字体类
        var chineseText = element.textContent
            .replace(/[^\u4e00-\u9fa5]+/g, "")
            .trim();
        if (chineseText) {
            var chineseSpan = document.createElement("span");
            chineseSpan.className = "cn-font";
            chineseSpan.textContent = chineseText;
            element.appendChild(chineseSpan);
        }
    });
}

// 在DOM加载完成后应用字体
document.addEventListener("DOMContentLoaded", applyFontsToText);
