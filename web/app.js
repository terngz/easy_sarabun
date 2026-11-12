/* Easy Sarabun Web — UI logic (browser glue only).
 * Handles drag & drop, mode switch, file queue, status, and downloads.
 */
(function () {
  'use strict';

  var dropzone = document.getElementById('dropzone');
  var fileInput = document.getElementById('file-input');
  var fileList = document.getElementById('file-list');
  var convertBtn = document.getElementById('convert-btn');
  var clearBtn = document.getElementById('clear-btn');
  var modeReverse = document.getElementById('mode-reverse');
  var modeFrom = document.getElementById('mode-from');
  var modeTo = document.getElementById('mode-to');
  var statusEl = document.getElementById('status');
  var modeExample = document.getElementById('mode-example');

  var files = []; // { file, ext }

  function setStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = 'status status-' + (type || 'info');
  }

  function refreshModeLabels() {
    if (modeReverse.checked) {
      modeFrom.textContent = 'ไทย ➔ อารบิก';
      modeTo.textContent = 'อารบิก ➔ ไทย';
      modeFrom.classList.add('active');
      modeTo.classList.remove('active');
      if (modeExample) modeExample.textContent = '๑ ๒ ๓ → 1 2 3';
    } else {
      modeFrom.textContent = 'อารบิก ➔ ไทย';
      modeTo.textContent = 'ไทย ➔ อารบิก';
      modeTo.classList.add('active');
      modeFrom.classList.remove('active');
      if (modeExample) modeExample.textContent = '1 2 3 → ๑ ๒ ๓';
    }
  }

  function refreshConvertBtn() {
    convertBtn.disabled = files.length === 0;
  }

  function renderList() {
    fileList.innerHTML = '';
    files.forEach(function (entry, i) {
      var ext = (entry.file.name.split('.').pop() || '').toLowerCase();
      var li = document.createElement('li');
      li.innerHTML = '<span class="file-name"></span><span class="file-badge"></span>' +
        '<button class="file-remove" aria-label="ลบ">×</button>';
      li.querySelector('.file-name').textContent = entry.file.name;
      li.querySelector('.file-badge').textContent = '.' + ext;
      li.querySelector('.file-remove').addEventListener('click', function () {
        files.splice(i, 1);
        renderList();
        refreshConvertBtn();
        if (files.length === 0) setStatus('เลือกไฟล์เพื่อเริ่มแปลง', 'info');
      });
      fileList.appendChild(li);
    });
    refreshConvertBtn();
  }

  function addFiles(list) {
    var added = 0;
    var rejected = 0;
    Array.prototype.forEach.call(list, function (file) {
      if (EasyWeb.is_supported(file.name)) {
        files.push({ file: file });
        added++;
      } else {
        rejected++;
      }
    });
    renderList();
    if (added > 0) {
      setStatus('เพิ่ม ' + added + ' ไฟล์แล้ว' + (rejected ? ' (ข้าม ' + rejected + ' ไฟล์ที่ไม่รองรับ)' : ''), 'info');
    } else if (rejected > 0) {
      setStatus('ไม่รองรับไฟล์ที่เลือก (' + rejected + ' ไฟล์)', 'err');
    }
  }

  // Dropzone interactions
  dropzone.addEventListener('click', function (e) {
    if (e.target !== fileInput) fileInput.click();
  });
  fileInput.addEventListener('change', function () {
    addFiles(fileInput.files);
    fileInput.value = '';
  });
  ['dragover', 'dragenter'].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });
  dropzone.addEventListener('drop', function (e) {
    addFiles(e.dataTransfer.files);
  });
  dropzone.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });

  // Mode
  modeReverse.addEventListener('change', refreshModeLabels);
  refreshModeLabels();

  // Clear
  clearBtn.addEventListener('click', function () {
    files = [];
    renderList();
    setStatus('ล้างรายการแล้ว', 'info');
  });

  // Convert
  convertBtn.addEventListener('click', async function () {
    if (files.length === 0) return;
    var reverse = modeReverse.checked;
    convertBtn.disabled = true;
    setStatus('กำลังแปลง...', 'info');
    var ok = 0, failed = 0;
    try {
      for (var i = 0; i < files.length; i++) {
        var entry = files[i];
        try {
          var result = await EasyWeb.convert_file(entry.file, reverse);
          downloadBlob(result.blob, result.name);
          ok++;
        } catch (e) {
          failed++;
          console.error('แปลงไม่สำเร็จ:', entry.file.name, e);
        }
      }
      if (failed === 0) {
        setStatus(ok > 1 ? 'แปลงสำเร็จ ' + ok + ' ไฟล์ — ไฟล์ถูกดาวน์โหลดแล้ว' : 'แปลงสำเร็จ — ไฟล์ถูกดาวน์โหลดแล้ว', 'ok');
      } else {
        setStatus('สำเร็จ ' + ok + ' ไฟล์ / ล้มเหลว ' + failed + ' ไฟล์', 'err');
      }
    } finally {
      refreshConvertBtn();
    }
  });

  // FAQ accordion — the download button is a plain <a href> link (footer), no JS needed.
  var faqItems = document.querySelectorAll('.faq-item');
  Array.prototype.forEach.call(faqItems, function (item, index) {
    var question = item.querySelector('.faq-q');
    var answer = item.querySelector('.faq-a');
    var questionText = question.textContent.replace(/\s+/g, ' ').trim();
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'faq-toggle';
    button.setAttribute('aria-controls', answer.id);
    item.classList.add('has-toggle');
    question.remove();
    item.insertBefore(button, answer);
    button.addEventListener('click', function () {
      var open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', open ? 'false' : 'true');
      answer.hidden = open;
    });
    button.textContent = questionText;
    // Collapse all, but leave the first ("วิธีใช้") open by default
    if (index === 0) {
      answer.hidden = false;
      button.setAttribute('aria-expanded', 'true');
    } else {
      answer.hidden = true;
      button.setAttribute('aria-expanded', 'false');
    }
  });

  function downloadBlob(blob, name) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
})();
