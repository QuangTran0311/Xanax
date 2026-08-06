import { runMatchPreview } from './knowledge.js';
import { showToast } from './modals.js';

// Skill file upload
// ════════════════════════════════════════
export function handleSkillFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    const ext = file.name.split('.').pop().toLowerCase();
    let parsed = null;

    if (ext === 'json') {
      try {
        parsed = JSON.parse(content);
        document.getElementById('skill-config').value = JSON.stringify(parsed, null, 2);
        if (parsed.name && !document.getElementById('skill-name').value)
          document.getElementById('skill-name').value = parsed.name;
        if (parsed.description && !document.getElementById('skill-description').value)
          document.getElementById('skill-description').value = parsed.description;
      } catch {
        showToast('Invalid JSON file', 'error');
        return;
      }
    } else if (ext === 'md' || ext === 'txt') {
      const lines = content.split('\n');
      const nameLine = lines.find(l => l.startsWith('# ') || l.startsWith('name:'));
      if (nameLine && !document.getElementById('skill-name').value) {
        document.getElementById('skill-name').value = nameLine.replace(/^#\s*|^name:\s*/i, '').trim();
      }
      // Auto-fill description from "description:" line or first paragraph after "## Mô tả" / "## Description"
      const descField = document.getElementById('skill-description');
      if (descField && !descField.value) {
        const descLine = lines.find(l => /^description:/i.test(l));
        if (descLine) {
          descField.value = descLine.replace(/^description:\s*/i, '').trim();
        } else {
          const descHeadIdx = lines.findIndex(l => /^##\s*(mô tả|description)/i.test(l));
          if (descHeadIdx !== -1) {
            const para = lines.slice(descHeadIdx + 1).find(l => l.trim() !== '');
            if (para) descField.value = para.trim();
          }
        }
      }
      document.getElementById('skill-config').value = JSON.stringify({ content }, null, 2);
    } else if (ext === 'yaml' || ext === 'yml') {
      document.getElementById('skill-config').value = JSON.stringify({ raw: content }, null, 2);
    }

    document.getElementById('skill-file-name').textContent = file.name;
    document.getElementById('skill-file-preview').style.display = 'flex';
    document.getElementById('skill-upload-zone').style.display = 'none';
  };
  reader.readAsText(file);
}

export function clearSkillFile() {
  document.getElementById('skill-file-input').value = '';
  document.getElementById('skill-file-preview').style.display = 'none';
  document.getElementById('skill-upload-zone').style.display = '';
}

// Drag-and-drop for upload zone
document.addEventListener('DOMContentLoaded', () => {
  const zone = document.getElementById('skill-upload-zone');
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) {
      const inp = document.getElementById('skill-file-input');
      const dt = new DataTransfer();
      dt.items.add(f);
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change'));
    }
  });
});

// Wire match preview listeners on card modal inputs
document.getElementById('card-title').addEventListener('input', runMatchPreview);
document.getElementById('card-desc').addEventListener('input', runMatchPreview);

// ════════════════════════════════════════
