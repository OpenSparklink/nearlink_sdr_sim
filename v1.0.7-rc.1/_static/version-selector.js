/**
 * 文档版本选择器。
 * 从 versions.json 读取可用版本列表, 在页面顶部显示下拉切换控件。
 */
document.addEventListener("DOMContentLoaded", function () {
  var rootPath = document.documentElement.dataset.content_root || "../";
  var jsonUrl = rootPath + "../versions.json";

  fetch(jsonUrl)
    .then(function (r) { return r.json(); })
    .then(function (versions) {
      if (!versions || versions.length < 2) return;

      var currentPath = window.location.pathname;
      var segments = currentPath.replace(/^\//, "").split("/");
      var repoSegments = [];
      // 找到 version segment: 跳过 GitHub Pages 仓库前缀
      var versionIdx = -1;
      for (var i = 0; i < segments.length; i++) {
        var isVersion = versions.some(function (v) { return v.version === segments[i]; });
        if (isVersion) { versionIdx = i; break; }
        repoSegments.push(segments[i]);
      }
      var currentVersion = versionIdx >= 0 ? segments[versionIdx] : "latest";
      var subPath = versionIdx >= 0 ? segments.slice(versionIdx + 1).join("/") : "";

      var select = document.createElement("select");
      select.className = "version-selector";
      select.setAttribute("aria-label", "选择文档版本");

      versions.forEach(function (v) {
        var opt = document.createElement("option");
        opt.value = v.version;
        opt.textContent = v.version;
        if (v.version === currentVersion) opt.selected = true;
        select.appendChild(opt);
      });

      select.addEventListener("change", function () {
        var prefix = repoSegments.length ? "/" + repoSegments.join("/") : "";
        window.location.href = prefix + "/" + this.value + "/" + subPath;
      });

      var container = document.createElement("div");
      container.className = "version-selector-container";
      var label = document.createElement("span");
      label.textContent = "版本: ";
      label.className = "version-label";
      container.appendChild(label);
      container.appendChild(select);

      var sidebar = document.querySelector(".sidebar-brand") ||
                    document.querySelector(".sidebar-sticky");
      if (sidebar) {
        sidebar.appendChild(container);
      }
    })
    .catch(function () { /* versions.json 不存在时静默失败 */ });

  // ── 语言切换器 ──
  (function () {
    var path = window.location.pathname;
    var isEn = /\/en\//.test(path);
    var btn = document.createElement("a");
    btn.className = "lang-switcher";
    btn.textContent = isEn ? "中文" : "English";
    btn.title = isEn ? "切换到中文" : "Switch to English";
    btn.href = "#";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      if (isEn) {
        window.location.href = path.replace(/\/en\//, "/");
      } else {
        // 在当前路径中找到版本号后插入 /en/
        var parts = path.split("/");
        var inserted = false;
        for (var i = 0; i < parts.length; i++) {
          if (/^\d+\.\d+/.test(parts[i]) || parts[i] === "latest") {
            parts.splice(i + 1, 0, "en");
            inserted = true;
            break;
          }
        }
        if (!inserted) {
          // 本地预览或无版本路径: 直接替换根目录为 en 子目录
          var base = path.replace(/\/[^/]*$/, "/en/");
          var tail = path.replace(/^.*\/([^/]*)$/, "$1");
          window.location.href = base + tail;
        } else {
          window.location.href = parts.join("/");
        }
      }
    });

    var sidebar = document.querySelector(".sidebar-brand") ||
                  document.querySelector(".sidebar-sticky");
    if (sidebar) {
      var langDiv = document.createElement("div");
      langDiv.className = "lang-switcher-container";
      langDiv.appendChild(btn);
      sidebar.appendChild(langDiv);
    }
  })();
});
