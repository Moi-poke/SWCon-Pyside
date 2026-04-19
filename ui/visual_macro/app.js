import {
  buildVisualMacroDocument,
  loadWorkspaceState,
  registerVisualMacroBlocks,
  serializeWorkspaceToProgram,
  updateTemplateDropdownOptions,
  getSelectedTemplatePath,
  setRoiOnSelectedBlock,
} from "./blocks.js";

let bridge = null;
let workspace = null;

let currentDocumentPath = "";
let isDocumentModified = false;
let suppressDirtyTracking = false;
let lastCleanDocumentSignature = "";

const RECENT_FILES_STORAGE_KEY = "visual_macro_recent_files";
const MAX_RECENT_FILES = 10;

/** Block ID targeted by the ROI modal (saved during preview update). */
let _roiTargetBlockId = null;

/** Template image natural size for minimum ROI enforcement. */
let _roiTemplateSize = null;

/** Current drag mode: 'new' | 'move' | 'handle-nw' | ... | null */
let _roiDragMode = null;

/** Offset from mouse to selection origin, used for move drag. */
let _roiMoveOffset = { dx: 0, dy: 0 };

function setStatus(message) {
  const element = document.getElementById("status-text");
  if (element) {
    element.innerText = message;
  }
}
function highlightExecutionBlock(blockId) {
  if (!workspace) {
    return;
  }
  workspace.highlightBlock(blockId || null);
}

function clearExecutionBlockHighlight() {
  if (!workspace) {
    return;
  }
  workspace.highlightBlock(null);
}
function getProgramTextArea() {
  const element = document.getElementById("program-json-output");
  if (!element) {
    throw new Error("program-json-output が見つかりません。");
  }
  return element;
}

function getFilePathInput() {
  const element = document.getElementById("file-path-input");
  if (!element) {
    throw new Error("file-path-input が見つかりません。");
  }
  return element;
}

function getTemplateSelect() {
  return document.getElementById("template-select");
}

function getRecentFilesButton() {
  return document.getElementById("recent-files-button");
}

function getRecentFilesMenu() {
  return document.getElementById("recent-files-menu");
}

function getMetadataNameInput() {
  return document.getElementById("meta-name-input");
}

function getMetadataDescriptionInput() {
  return document.getElementById("meta-description-input");
}

function getMetadataTagsInput() {
  return document.getElementById("meta-tags-input");
}

function updateFilePathInput(path) {
  const input = getFilePathInput();
  input.value = path || "";
}

function bridgeCall(methodName, args = []) {
  return new Promise((resolve, reject) => {
    if (!bridge) {
      reject(new Error("PySide 未接続"));
      return;
    }

    const method = bridge[methodName];
    if (typeof method !== "function") {
      reject(new Error(`Bridge method not found: ${methodName}`));
      return;
    }

    try {
      method.call(bridge, ...args, (result) => {
        resolve(result);
      });
    } catch (error) {
      reject(error instanceof Error ? error : new Error(String(error)));
    }
  });
}

function notifyDocumentState() {
  if (bridge && typeof bridge.update_document_state === "function") {
    bridge.update_document_state(currentDocumentPath, isDocumentModified);
  }
}

function updateEditorCaption() {
  const metadata = getMetadataFromUi();
  const nameFromMetadata = metadata.name || "";
  const baseName = currentDocumentPath
    ? currentDocumentPath.replaceAll("\\", "/").split("/").pop()
    : "無題";
  const displayName = nameFromMetadata || baseName;
  const suffix = isDocumentModified ? " *" : "";
  setStatus(`編集中: ${displayName}${suffix}`);
}

function getMetadataFromUi() {
  const nameInput = getMetadataNameInput();
  const descriptionInput = getMetadataDescriptionInput();
  const tagsInput = getMetadataTagsInput();

  const rawTags = tagsInput?.value || "";
  const tags = rawTags
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value !== "");

  return {
    name: nameInput?.value?.trim() || "",
    description: descriptionInput?.value?.trim() || "",
    tags,
  };
}

function setMetadataToUi(metadata) {
  const nameInput = getMetadataNameInput();
  const descriptionInput = getMetadataDescriptionInput();
  const tagsInput = getMetadataTagsInput();

  if (nameInput) {
    nameInput.value = metadata?.name || "";
  }
  if (descriptionInput) {
    descriptionInput.value = metadata?.description || "";
  }
  if (tagsInput) {
    tagsInput.value = Array.isArray(metadata?.tags)
      ? metadata.tags.join(", ")
      : "";
  }
}

function clearMetadataUi() {
  setMetadataToUi({
    name: "",
    description: "",
    tags: [],
  });
}

function buildVisualMacroDocumentWithMetadata() {
  const baseDocument = buildVisualMacroDocument(workspace);
  return {
    ...baseDocument,
    metadata: getMetadataFromUi(),
  };
}

function computeCurrentDocumentSignature() {
  return JSON.stringify(buildVisualMacroDocumentWithMetadata());
}

function applyDocumentState(path, modified) {
  currentDocumentPath = path || "";
  isDocumentModified = Boolean(modified);
  updateFilePathInput(currentDocumentPath);
  updateEditorCaption();
  notifyDocumentState();
}

function markCurrentDocumentAsClean(path) {
  currentDocumentPath = path || "";
  lastCleanDocumentSignature = computeCurrentDocumentSignature();
  applyDocumentState(currentDocumentPath, false);
}

function syncDirtyStateFromWorkspace() {
  const currentSignature = computeCurrentDocumentSignature();
  const modified = currentSignature !== lastCleanDocumentSignature;
  if (modified !== isDocumentModified) {
    applyDocumentState(currentDocumentPath, modified);
  }
}

function markDirtyFromMetadataChange() {
  if (suppressDirtyTracking) {
    return;
  }
  syncDirtyStateFromWorkspace();
}

function setupMetadataInputs() {
  const nameInput = getMetadataNameInput();
  const descriptionInput = getMetadataDescriptionInput();
  const tagsInput = getMetadataTagsInput();

  const handler = () => {
    try {
      updateEditorCaption();
      markDirtyFromMetadataChange();
    } catch (error) {
      console.error("[VisualMacro] Metadata change failed:", error);
      setStatus(`メタデータ更新失敗: ${error.message}`);
    }
  };

  nameInput?.addEventListener("input", handler);
  descriptionInput?.addEventListener("input", handler);
  tagsInput?.addEventListener("input", handler);
}

function confirmDiscardIfNeeded() {
  if (!isDocumentModified) {
    return true;
  }
  return window.confirm("未保存の変更があります。破棄して続行しますか？");
}

async function loadToolbox() {
  const response = await fetch("./toolbox.json");
  if (!response.ok) {
    throw new Error(`toolbox.json の読込に失敗しました: ${response.status}`);
  }
  return await response.json();
}

function refreshProgramJson() {
  const output = getProgramTextArea();
  const program = serializeWorkspaceToProgram(workspace);
  const jsonText = JSON.stringify(program, null, 2);
  output.value = jsonText;
  return jsonText;
}

function populateTemplateList(entries) {
  const select = getTemplateSelect();
  if (!select) {
    return;
  }

  select.innerHTML = "";
  for (const entry of entries) {
    const option = document.createElement("option");
    option.value = entry.relative_path;
    option.textContent = entry.relative_path;
    select.appendChild(option);
  }
}

async function refreshTemplateList() {
  try {
    const jsonText = await bridgeCall("get_template_list_json");
    const entries = JSON.parse(jsonText);
    populateTemplateList(entries);
    updateTemplateDropdownOptions(entries);
    setStatus("テンプレート一覧を更新しました");
    notifyDocumentState();
  } catch (error) {
    console.error("[VisualMacro] Template list load failed:", error);
    setStatus(`テンプレート一覧更新失敗: ${error.message}`);
  }
}

function normalizeLoadedDocument(rawValue) {
  if (!rawValue || typeof rawValue !== "object" || Array.isArray(rawValue)) {
    throw new Error("読込データは JSON オブジェクトである必要があります。");
  }

  if (rawValue.format === "visual_macro_document") {
    if (!("program" in rawValue)) {
      throw new Error("読込 document に program がありません。");
    }
    if (!("workspace" in rawValue)) {
      throw new Error("読込 document に workspace がありません。");
    }
    return {
      ...rawValue,
      metadata:
        rawValue.metadata && typeof rawValue.metadata === "object"
          ? rawValue.metadata
          : {
              name: "",
              description: "",
              tags: [],
            },
    };
  }

  if ("version" in rawValue && "root" in rawValue) {
    return {
      format: "visual_macro_document",
      version: "1.0",
      metadata: {
        name: "",
        description: "",
        tags: [],
      },
      workspace: {},
      program: rawValue,
    };
  }

  throw new Error("未対応の保存形式です。");
}

function pathToRecentDisplayName(path) {
  const normalized = (path || "").replaceAll("\\", "/");
  const parts = normalized.split("/");

  if (parts.length <= 1) {
    return normalized;
  }

  const fileName = parts[parts.length - 1];
  const parentName = parts[parts.length - 2];
  return `${parentName}/${fileName}`;
}

function loadRecentFiles() {
  try {
    const raw = window.localStorage.getItem(RECENT_FILES_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(
      (value) => typeof value === "string" && value.trim() !== "",
    );
  } catch (error) {
    console.warn("[VisualMacro] Failed to load recent files:", error);
    return [];
  }
}

function saveRecentFiles(recentFiles) {
  window.localStorage.setItem(
    RECENT_FILES_STORAGE_KEY,
    JSON.stringify(recentFiles.slice(0, MAX_RECENT_FILES)),
  );
}

function addRecentFile(path) {
  const normalized = (path || "").trim();
  if (!normalized) {
    return;
  }

  const recentFiles = loadRecentFiles().filter((item) => item !== normalized);
  recentFiles.unshift(normalized);
  saveRecentFiles(recentFiles);
  refreshRecentFilesUi();
}

function removeRecentFile(path) {
  const normalized = (path || "").trim();
  if (!normalized) {
    return;
  }

  const recentFiles = loadRecentFiles().filter((item) => item !== normalized);
  saveRecentFiles(recentFiles);
  refreshRecentFilesUi();
}

function refreshRecentFilesUi() {
  const button = getRecentFilesButton();
  const menu = getRecentFilesMenu();
  if (!button || !menu) {
    return;
  }

  const recentFiles = loadRecentFiles();
  menu.innerHTML = "";

  if (recentFiles.length === 0) {
    const empty = document.createElement("div");
    empty.className = "recent-files-item";
    empty.textContent = "最近使ったファイルはありません";
    empty.title = "";
    empty.style.cursor = "default";
    menu.appendChild(empty);

    button.textContent = "最近使ったファイル";
    button.title = "";
    return;
  }

  for (const path of recentFiles) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "recent-files-item";
    item.textContent = pathToRecentDisplayName(path);
    item.title = path;

    item.addEventListener("click", async () => {
      menu.hidden = true;
      await openDocumentByPath(path, {
        confirmDiscard: true,
        updateRecent: true,
      });
    });

    menu.appendChild(item);
  }

  button.textContent = "最近使ったファイル";
  button.title = "";
}

function setupRecentFilesDropdown() {
  const button = getRecentFilesButton();
  const menu = getRecentFilesMenu();
  if (!button || !menu) {
    return;
  }

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    menu.hidden = !menu.hidden;
  });

  menu.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }

    if (!button.contains(target) && !menu.contains(target)) {
      menu.hidden = true;
    }
  });
}

async function chooseOpenDocumentPath() {
  return await bridgeCall("choose_open_document_path");
}

async function chooseSaveDocumentPath(suggestedPath = "") {
  return await bridgeCall("choose_save_document_path", [suggestedPath]);
}

async function openDocumentByPath(relativePath, options = {}) {
  const { confirmDiscard = true, updateRecent = true } = options;
  const normalizedPath = (relativePath || "").trim();

  if (!normalizedPath) {
    setStatus("読込ファイル名を入力してください");
    return false;
  }

  if (confirmDiscard && !confirmDiscardIfNeeded()) {
    return false;
  }

  try {
    updateFilePathInput(normalizedPath);

    const content = await bridgeCall("load_visual_macro_document_json", [
      normalizedPath,
    ]);
    if (!content) {
      return false;
    }

    const rawValue = JSON.parse(content);
    const documentObject = normalizeLoadedDocument(rawValue);
    const documentText = JSON.stringify(documentObject, null, 2);

    const isDocumentValid = await bridgeCall(
      "validate_visual_macro_document_json",
      [documentText],
    );
    if (!isDocumentValid) {
      return false;
    }

    suppressDirtyTracking = true;

    setMetadataToUi(documentObject.metadata || {});
    loadWorkspaceState(workspace, documentObject.workspace);
    getProgramTextArea().value = JSON.stringify(
      documentObject.program,
      null,
      2,
    );
    setStatus("Visual Macro を読み込みました");

    window.setTimeout(() => {
      try {
        markCurrentDocumentAsClean(normalizedPath);
        if (updateRecent) {
          addRecentFile(normalizedPath);
        }
      } finally {
        suppressDirtyTracking = false;
      }
    }, 0);

    return true;
  } catch (error) {
    console.error("[VisualMacro] Load failed:", error);
    setStatus(`読込失敗: ${error.message}`);
    removeRecentFile(normalizedPath);
    suppressDirtyTracking = false;
    return false;
  }
}

async function saveCurrentDocument() {
  let relativePath = currentDocumentPath || getFilePathInput().value.trim();

  if (!relativePath) {
    relativePath = await chooseSaveDocumentPath("sample_macro.json");
    if (!relativePath) {
      return false;
    }
    updateFilePathInput(relativePath);
  }

  const documentObject = buildVisualMacroDocumentWithMetadata();
  const documentText = JSON.stringify(documentObject, null, 2);

  const ok = await bridgeCall("save_visual_macro_document_json", [
    relativePath,
    documentText,
  ]);
  if (!ok) {
    setStatus("保存に失敗しました");
    return false;
  }

  markCurrentDocumentAsClean(relativePath);
  addRecentFile(relativePath);
  setStatus("保存しました");
  return true;
}

async function saveCurrentDocumentAs() {
  const suggestedPath =
    currentDocumentPath ||
    getFilePathInput().value.trim() ||
    "sample_macro.json";

  const relativePath = await chooseSaveDocumentPath(suggestedPath);
  if (!relativePath) {
    return false;
  }

  updateFilePathInput(relativePath);

  const documentObject = buildVisualMacroDocumentWithMetadata();
  const documentText = JSON.stringify(documentObject, null, 2);

  const ok = await bridgeCall("save_visual_macro_document_json", [
    relativePath,
    documentText,
  ]);
  if (!ok) {
    setStatus("名前を付けて保存に失敗しました");
    return false;
  }

  markCurrentDocumentAsClean(relativePath);
  addRecentFile(relativePath);
  setStatus("名前を付けて保存しました");
  return true;
}

async function initializeBlockly() {
  registerVisualMacroBlocks();

  const toolbox = await loadToolbox();
  workspace = Blockly.inject("blockly-div", {
    toolbox,
    trashcan: true,
    scrollbars: true,
    sounds: false,
    zoom: {
      controls: true,
      wheel: true,
      startScale: 1.0,
      maxScale: 2.0,
      minScale: 0.5,
      scaleSpeed: 1.1,
    },
    move: {
      scrollbars: true,
      drag: true,
      wheel: true,
    },
  });

  workspace.addChangeListener(() => {
    try {
      refreshProgramJson();

      // --- Template preview listener ---
      workspace.addChangeListener((event) => {
        if (event.type === Blockly.Events.SELECTED) {
          if (event.newElementId) {
            updateTemplatePreview();
          }
          return;
        }
        // Update preview when template dropdown value changes on selected block
        if (
          event.type === Blockly.Events.BLOCK_CHANGE &&
          event.element === "field" &&
          (event.name === "TEMPLATE" || event.name === "template")
        ) {
          updateTemplatePreview();
        }
      });

      if (suppressDirtyTracking) {
        return;
      }

      syncDirtyStateFromWorkspace();
    } catch (error) {
      console.error("[VisualMacro] Program JSON refresh failed:", error);
      setStatus(`JSON更新失敗: ${error.message}`);
    }
  });

  refreshProgramJson();
  markCurrentDocumentAsClean(getFilePathInput().value.trim());
}

// ── ROI Modal ──

let _roiImage = null;
let _roiScale = 1;
let _roiSelection = null; // {x1,y1,x2,y2} in original image coords
let _roiDragging = false;
let _roiDragStart = null; // {x,y} in canvas coords

function getRoiModal() {
  return document.getElementById("roi-modal");
}
function getRoiCanvas() {
  return document.getElementById("roi-canvas");
}
function getRoiCanvasWrapper() {
  return document.getElementById("roi-canvas-wrapper");
}
function getRoiCoordsDisplay() {
  return document.getElementById("roi-coords-display");
}
function getRoiInfoText() {
  return document.getElementById("roi-info-text");
}
function getRoiApplyBtn() {
  return document.getElementById("roi-apply-btn");
}
function getRoiSelectBtn() {
  return document.getElementById("roi-select-btn");
}

function openRoiModal() {
  const modal = getRoiModal();
  if (!modal) return;
  _roiImage = null;
  _roiSelection = null;
  _roiDragging = false;
  _roiDragMode = null;
  syncRoiToInputs();

  // Pre-load existing ROI values from selected block
  const selected = _roiTargetBlockId
    ? workspace.getBlockById(_roiTargetBlockId)
    : null;
  if (selected && selected.getField("TRIM_X1")) {
    const x1 = Number(selected.getFieldValue("TRIM_X1") || 0);
    const y1 = Number(selected.getFieldValue("TRIM_Y1") || 0);
    const x2 = Number(selected.getFieldValue("TRIM_X2") || 0);
    const y2 = Number(selected.getFieldValue("TRIM_Y2") || 0);
    if (x1 !== 0 || y1 !== 0 || x2 !== 0 || y2 !== 0) {
      _roiSelection = { x1, y1, x2, y2 };
    }
  }

  modal.hidden = false;
  clearRoiCanvas();
  updateRoiCoordsDisplay();
  getRoiInfoText().textContent = "画像を読み込んでください";
  getRoiApplyBtn().disabled = true;
}

function closeRoiModal() {
  const modal = getRoiModal();
  if (modal) modal.hidden = true;
  _roiImage = null;
  _roiSelection = null;
  _roiDragging = false;
}

function clearRoiCanvas() {
  const canvas = getRoiCanvas();
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  canvas.width = 300;
  canvas.height = 200;
  ctx.fillStyle = "#f0f0f0";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#999";
  ctx.font = "14px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("📷 または 📁 で画像を読み込み", 150, 105);
}

function loadImageOntoCanvas(imgElement) {
  _roiImage = imgElement;
  const canvas = getRoiCanvas();
  const wrapper = getRoiCanvasWrapper();
  if (!canvas || !wrapper) return;

  const wrapperRect = wrapper.getBoundingClientRect();
  const maxW = wrapperRect.width - 4;
  const maxH = wrapperRect.height - 4;

  const imgW = imgElement.naturalWidth;
  const imgH = imgElement.naturalHeight;

  _roiScale = Math.min(maxW / imgW, maxH / imgH, 1);
  canvas.width = Math.round(imgW * _roiScale);
  canvas.height = Math.round(imgH * _roiScale);

  drawRoiOverlay();
  getRoiInfoText().textContent = `${imgW}×${imgH} px (表示: ${canvas.width}×${canvas.height})`;

  if (_roiSelection) {
    updateRoiCoordsDisplay();
    getRoiApplyBtn().disabled = false;
  }
}

function drawRoiOverlay() {
  const canvas = getRoiCanvas();
  if (!canvas || !_roiImage) return;
  const ctx = canvas.getContext("2d");

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(_roiImage, 0, 0, canvas.width, canvas.height);

  if (!_roiSelection) return;
  const scaleX = canvas.width / (_roiImage.naturalWidth || _roiImage.width);
  const scaleY = canvas.height / (_roiImage.naturalHeight || _roiImage.height);
  const cx1 = _roiSelection.x1 * scaleX,
    cy1 = _roiSelection.y1 * scaleY;
  const cx2 = _roiSelection.x2 * scaleX,
    cy2 = _roiSelection.y2 * scaleY;

  ctx.fillStyle = "rgba(0,0,0,0.45)";
  ctx.fillRect(0, 0, canvas.width, cy1);
  ctx.fillRect(0, cy2, canvas.width, canvas.height - cy2);
  ctx.fillRect(0, cy1, cx1, cy2 - cy1);
  ctx.fillRect(cx2, cy1, canvas.width - cx2, cy2 - cy1);

  ctx.strokeStyle = "#00ff88";
  ctx.lineWidth = 2;
  ctx.strokeRect(cx1, cy1, cx2 - cx1, cy2 - cy1);
  drawResizeHandles(ctx, cx1, cy1, cx2, cy2);
}

const HANDLE_SIZE = 8;
const HANDLE_HIT = 12;

function drawResizeHandles(ctx, cx1, cy1, cx2, cy2) {
  const midX = (cx1 + cx2) / 2,
    midY = (cy1 + cy2) / 2,
    hs = HANDLE_SIZE / 2;
  const handles = [
    [cx1, cy1],
    [midX, cy1],
    [cx2, cy1],
    [cx1, midY],
    [cx2, midY],
    [cx1, cy2],
    [midX, cy2],
    [cx2, cy2],
  ];
  for (const [hx, hy] of handles) {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(hx - hs, hy - hs, HANDLE_SIZE, HANDLE_SIZE);
    ctx.strokeStyle = "#333333";
    ctx.lineWidth = 1;
    ctx.strokeRect(hx - hs, hy - hs, HANDLE_SIZE, HANDLE_SIZE);
  }
}

function getHandleAtPosition(canvasX, canvasY) {
  if (!_roiSelection || !_roiImage) return null;
  const canvas = getRoiCanvas();
  if (!canvas) return null;
  const scaleX = canvas.width / (_roiImage.naturalWidth || _roiImage.width);
  const scaleY = canvas.height / (_roiImage.naturalHeight || _roiImage.height);
  const cx1 = _roiSelection.x1 * scaleX,
    cy1 = _roiSelection.y1 * scaleY;
  const cx2 = _roiSelection.x2 * scaleX,
    cy2 = _roiSelection.y2 * scaleY;
  const midX = (cx1 + cx2) / 2,
    midY = (cy1 + cy2) / 2,
    hh = HANDLE_HIT / 2;
  const pts = [
    ["nw", cx1, cy1],
    ["n", midX, cy1],
    ["ne", cx2, cy1],
    ["w", cx1, midY],
    ["e", cx2, midY],
    ["sw", cx1, cy2],
    ["s", midX, cy2],
    ["se", cx2, cy2],
  ];
  for (const [name, hx, hy] of pts) {
    if (
      canvasX >= hx - hh &&
      canvasX <= hx + hh &&
      canvasY >= hy - hh &&
      canvasY <= hy + hh
    )
      return name;
  }
  return null;
}

function isInsideRoiSelection(canvasX, canvasY) {
  if (!_roiSelection || !_roiImage) return false;
  const canvas = getRoiCanvas();
  if (!canvas) return false;
  const scaleX = canvas.width / (_roiImage.naturalWidth || _roiImage.width);
  const scaleY = canvas.height / (_roiImage.naturalHeight || _roiImage.height);
  const cx1 = _roiSelection.x1 * scaleX,
    cy1 = _roiSelection.y1 * scaleY;
  const cx2 = _roiSelection.x2 * scaleX,
    cy2 = _roiSelection.y2 * scaleY;
  return canvasX >= cx1 && canvasX <= cx2 && canvasY >= cy1 && canvasY <= cy2;
}

const HANDLE_CURSORS = {
  nw: "nwse-resize",
  se: "nwse-resize",
  ne: "nesw-resize",
  sw: "nesw-resize",
  n: "ns-resize",
  s: "ns-resize",
  e: "ew-resize",
  w: "ew-resize",
};

function canvasToImageCoords(canvasX, canvasY) {
  if (_roiScale === 0) return { x: 0, y: 0 };
  const imgW = _roiImage ? _roiImage.naturalWidth : 0;
  const imgH = _roiImage ? _roiImage.naturalHeight : 0;
  return {
    x: Math.max(0, Math.min(Math.round(canvasX / _roiScale), imgW)),
    y: Math.max(0, Math.min(Math.round(canvasY / _roiScale), imgH)),
  };
}

function updateRoiCoordsDisplay() {
  const el = document.getElementById("roi-coords-display");
  if (_roiSelection) {
    const x1 = Math.round(_roiSelection.x1),
      y1 = Math.round(_roiSelection.y1);
    const x2 = Math.round(_roiSelection.x2),
      y2 = Math.round(_roiSelection.y2);
    if (el)
      el.textContent = `(${x1}, ${y1})-(${x2}, ${y2})  [${x2 - x1}×${y2 - y1}]`;
    syncRoiToInputs();
  } else {
    if (el) el.textContent = "";
    syncRoiToInputs();
  }
}

/** Write _roiSelection coords to the input fields. */
function syncRoiToInputs() {
  const ids = ["roi-input-x1", "roi-input-y1", "roi-input-x2", "roi-input-y2"];
  const vals = _roiSelection
    ? [
        _roiSelection.x1,
        _roiSelection.y1,
        _roiSelection.x2,
        _roiSelection.y2,
      ].map(Math.round)
    : [0, 0, 0, 0];
  ids.forEach((id, i) => {
    const el = document.getElementById(id);
    if (el) el.value = vals[i];
  });
}

function syncRoiFromInputs() {
  const x1 = Number(document.getElementById("roi-input-x1")?.value || 0);
  const y1 = Number(document.getElementById("roi-input-y1")?.value || 0);
  const x2 = Number(document.getElementById("roi-input-x2")?.value || 0);
  const y2 = Number(document.getElementById("roi-input-y2")?.value || 0);
  if (x2 > x1 && y2 > y1) {
    _roiSelection = { x1, y1, x2, y2 };
    clampRoiSelection();
    drawRoiOverlay();
    updateRoiCoordsDisplay();
    getRoiApplyBtn().disabled = false;
  }
}

/** Enforce minimum ROI size based on template dimensions. */
function clampRoiSelection() {
  if (!_roiSelection || !_roiImage) return;
  const imgW = _roiImage.naturalWidth || _roiImage.width;
  const imgH = _roiImage.naturalHeight || _roiImage.height;
  const minW = _roiTemplateSize ? _roiTemplateSize.width : 1;
  const minH = _roiTemplateSize ? _roiTemplateSize.height : 1;

  // Ensure x1 < x2, y1 < y2
  let { x1, y1, x2, y2 } = _roiSelection;
  if (x1 > x2) [x1, x2] = [x2, x1];
  if (y1 > y2) [y1, y2] = [y2, y1];
  if (x2 - x1 < minW) {
    const cx = (x1 + x2) / 2;
    x1 = cx - minW / 2;
    x2 = cx + minW / 2;
  }
  if (y2 - y1 < minH) {
    const cy = (y1 + y2) / 2;
    y1 = cy - minH / 2;
    y2 = cy + minH / 2;
  }
  if (x1 < 0) {
    x2 -= x1;
    x1 = 0;
  }
  if (y1 < 0) {
    y2 -= y1;
    y1 = 0;
  }
  if (x2 > imgW) {
    x1 -= x2 - imgW;
    x2 = imgW;
  }
  if (y2 > imgH) {
    y1 -= y2 - imgH;
    y2 = imgH;
  }
  x1 = Math.max(0, x1);
  y1 = Math.max(0, y1);
  _roiSelection = { x1, y1, x2, y2 };
}

function setupRoiCanvasEvents() {
  const canvas = getRoiCanvas();
  if (!canvas) return;
  let dragStartImgX = 0,
    dragStartImgY = 0;

  function canvasToImage(e) {
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left,
      cy = e.clientY - rect.top;
    const imgW = _roiImage
      ? _roiImage.naturalWidth || _roiImage.width
      : canvas.width;
    const imgH = _roiImage
      ? _roiImage.naturalHeight || _roiImage.height
      : canvas.height;
    return {
      canvasX: cx,
      canvasY: cy,
      imgX: Math.max(0, Math.min(imgW, (cx * imgW) / canvas.width)),
      imgY: Math.max(0, Math.min(imgH, (cy * imgH) / canvas.height)),
    };
  }

  canvas.addEventListener("mousedown", (e) => {
    if (!_roiImage) return;
    const { canvasX, canvasY, imgX, imgY } = canvasToImage(e);

    // Priority 1: resize handle
    const handle = getHandleAtPosition(canvasX, canvasY);
    if (handle) {
      _roiDragMode = "handle-" + handle;
      dragStartImgX = imgX;
      dragStartImgY = imgY;
      _roiDragging = true;
      return;
    }

    // Priority 2: move existing selection
    if (isInsideRoiSelection(canvasX, canvasY)) {
      _roiDragMode = "move";
      _roiMoveOffset = {
        dx: imgX - _roiSelection.x1,
        dy: imgY - _roiSelection.y1,
      };
      _roiDragging = true;
      return;
    }

    // Priority 3: new selection
    _roiDragMode = "new";
    _roiSelection = { x1: imgX, y1: imgY, x2: imgX, y2: imgY };
    dragStartImgX = imgX;
    dragStartImgY = imgY;
    _roiDragging = true;
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!_roiImage) return;
    const { canvasX, canvasY, imgX, imgY } = canvasToImage(e);

    // Hover cursor
    if (!_roiDragging) {
      // Update cursor based on handle hover
      const handle = getHandleAtPosition(canvasX, canvasY);
      if (handle) {
        canvas.style.cursor = HANDLE_CURSORS[handle] || "pointer";
      } else if (isInsideRoiSelection(canvasX, canvasY)) {
        canvas.style.cursor = "move";
      } else {
        canvas.style.cursor = "crosshair";
      }
      return;
    }

    if (_roiDragMode === "new") {
      _roiSelection = {
        x1: Math.min(dragStartImgX, imgX),
        y1: Math.min(dragStartImgY, imgY),
        x2: Math.max(dragStartImgX, imgX),
        y2: Math.max(dragStartImgY, imgY),
      };
    } else if (_roiDragMode === "move" && _roiSelection) {
      const imgW = _roiImage.naturalWidth || _roiImage.width;
      const imgH = _roiImage.naturalHeight || _roiImage.height;
      const w = _roiSelection.x2 - _roiSelection.x1;
      const h = _roiSelection.y2 - _roiSelection.y1;
      let newX1 = imgX - _roiMoveOffset.dx;
      let newY1 = imgY - _roiMoveOffset.dy;
      // Clamp to image bounds while keeping size
      newX1 = Math.max(0, Math.min(imgW - w, newX1));
      newY1 = Math.max(0, Math.min(imgH - h, newY1));
      _roiSelection = { x1: newX1, y1: newY1, x2: newX1 + w, y2: newY1 + h };
    } else if (
      _roiDragMode &&
      _roiDragMode.startsWith("handle-") &&
      _roiSelection
    ) {
      const hType = _roiDragMode.slice(7);
      const minW = _roiTemplateSize ? _roiTemplateSize.width : 1;
      const minH = _roiTemplateSize ? _roiTemplateSize.height : 1;
      let { x1, y1, x2, y2 } = _roiSelection;

      if (hType.includes("w")) {
        x1 = Math.min(imgX, x2 - minW);
      }
      if (hType.includes("e")) {
        x2 = Math.max(imgX, x1 + minW);
      }
      if (hType === "n" || hType === "nw" || hType === "ne") {
        y1 = Math.min(imgY, y2 - minH);
      }
      if (hType === "s" || hType === "sw" || hType === "se") {
        y2 = Math.max(imgY, y1 + minH);
      }

      _roiSelection = { x1, y1, x2, y2 };
    }

    drawRoiOverlay();
    updateRoiCoordsDisplay();
  });

  canvas.addEventListener("mouseup", () => {
    if (_roiDragging && _roiSelection) {
      clampRoiSelection();
      drawRoiOverlay();
      updateRoiCoordsDisplay();
      getRoiApplyBtn().disabled = false;
    }
    _roiDragging = false;
    _roiDragMode = null;
  });

  canvas.addEventListener("mouseleave", () => {
    if (_roiDragging && _roiSelection) {
      clampRoiSelection();
      drawRoiOverlay();
      updateRoiCoordsDisplay();
      getRoiApplyBtn().disabled = false;
    }
    _roiDragging = false;
    _roiDragMode = null;
  });
}

function setupRoiModal() {
  setupRoiCanvasEvents();

  const selectBtn = getRoiSelectBtn();
  selectBtn?.addEventListener("click", () => {
    openRoiModal();
  });

  document
    .getElementById("roi-capture-btn")
    ?.addEventListener("click", async () => {
      if (!bridge) {
        getRoiInfoText().textContent = "PySide 未接続";
        return;
      }
      try {
        getRoiInfoText().textContent = "キャプチャ取得中...";
        const base64 = await bridgeCall("get_current_frame_base64");
        if (!base64) {
          getRoiInfoText().textContent = "キャプチャフレームがありません";
          return;
        }
        const img = new Image();
        img.onload = () => {
          loadImageOntoCanvas(img);
        };
        img.onerror = () => {
          getRoiInfoText().textContent = "画像読み込みに失敗しました";
        };
        img.src = "data:image/png;base64," + base64;
      } catch (error) {
        getRoiInfoText().textContent = `キャプチャ取得失敗: ${error.message}`;
      }
    });

  const fileInput = document.getElementById("roi-file-input");
  document
    .getElementById("roi-load-file-btn")
    ?.addEventListener("click", () => {
      fileInput?.click();
    });
  fileInput?.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const img = new Image();
      img.onload = () => {
        loadImageOntoCanvas(img);
      };
      img.onerror = () => {
        getRoiInfoText().textContent = "画像読み込みに失敗しました";
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
    fileInput.value = "";
  });

  document.getElementById("roi-apply-btn")?.addEventListener("click", () => {
    if (_roiSelection && workspace && _roiTargetBlockId) {
      const block = workspace.getBlockById(_roiTargetBlockId);
      if (block && block.getField("TRIM_X1")) {
        block.setFieldValue(String(Math.round(_roiSelection.x1)), "TRIM_X1");
        block.setFieldValue(String(Math.round(_roiSelection.y1)), "TRIM_Y1");
        block.setFieldValue(String(Math.round(_roiSelection.x2)), "TRIM_X2");
        block.setFieldValue(String(Math.round(_roiSelection.y2)), "TRIM_Y2");
        setStatus("ROI を適用しました");
      } else {
        setStatus("ROI の適用に失敗しました（対象ブロックが見つかりません）");
      }
    }
    closeRoiModal();
  });

  document.getElementById("roi-reset-btn")?.addEventListener("click", () => {
    _roiSelection = null;
    drawRoiOverlay();
    updateRoiCoordsDisplay();
    getRoiApplyBtn().disabled = true;
  });

  document.getElementById("roi-cancel-btn")?.addEventListener("click", () => {
    closeRoiModal();
  });

  // --- ROI coordinate input listeners ---
  ["roi-input-x1", "roi-input-y1", "roi-input-x2", "roi-input-y2"].forEach(
    (id) => {
      document.getElementById(id)?.addEventListener("input", () => {
        syncRoiFromInputs();
      });
    },
  );

  // --- Close ROI modal on overlay mousedown+mouseup ---
  const roiModalOverlay = getRoiModal
    ? getRoiModal()
    : document.getElementById("roi-modal");
  if (roiModalOverlay) {
    let _overlayMouseDownTarget = null;
    roiModalOverlay.addEventListener("mousedown", (e) => {
      _overlayMouseDownTarget = e.target;
    });
    roiModalOverlay.addEventListener("mouseup", (e) => {
      if (
        _overlayMouseDownTarget === roiModalOverlay &&
        e.target === roiModalOverlay
      ) {
        closeRoiModal();
      }
      _overlayMouseDownTarget = null;
    });
  }
}

function setupButtons() {
  const newButton = document.getElementById("new-button");
  const loadButton = document.getElementById("load-button");
  const saveButton = document.getElementById("save-button");
  const saveAsButton = document.getElementById("save-as-button");
  const runButton = document.getElementById("run-button");
  const stopButton = document.getElementById("stop-button");
  const refreshTemplatesButton = document.getElementById(
    "refresh-templates-button",
  );

  newButton?.addEventListener("click", () => {
    if (!workspace) {
      return;
    }
    if (!confirmDiscardIfNeeded()) {
      return;
    }

    suppressDirtyTracking = true;
    try {
      clearMetadataUi();
      workspace.clear();
      refreshProgramJson();
      setStatus("新規作成しました");
    } catch (error) {
      console.error("[VisualMacro] New workspace failed:", error);
      setStatus(`新規作成失敗: ${error.message}`);
    } finally {
      window.setTimeout(() => {
        try {
          markCurrentDocumentAsClean("");
        } finally {
          suppressDirtyTracking = false;
        }
      }, 0);
    }
  });

  loadButton?.addEventListener("click", async () => {
    const relativePath = await chooseOpenDocumentPath();
    if (!relativePath) {
      return;
    }

    await openDocumentByPath(relativePath, {
      confirmDiscard: true,
      updateRecent: true,
    });
  });

  saveButton?.addEventListener("click", async () => {
    try {
      await saveCurrentDocument();
    } catch (error) {
      console.error("[VisualMacro] Save failed:", error);
      setStatus(`保存失敗: ${error.message}`);
    }
  });

  saveAsButton?.addEventListener("click", async () => {
    try {
      await saveCurrentDocumentAs();
    } catch (error) {
      console.error("[VisualMacro] Save As failed:", error);
      setStatus(`名前を付けて保存失敗: ${error.message}`);
    }
  });

  runButton?.addEventListener("click", async () => {
    if (!bridge) {
      setStatus("PySide 未接続");
      return;
    }

    try {
      const programJson = refreshProgramJson();
      const isValid = await bridgeCall("validate_program_json", [programJson]);
      if (!isValid) {
        return;
      }

      bridge.request_run(programJson);
      setStatus("実行要求送信");
      notifyDocumentState();
    } catch (error) {
      console.error("[VisualMacro] Run failed:", error);
      setStatus(`実行失敗: ${error.message}`);
    }
  });

  stopButton?.addEventListener("click", () => {
    if (!bridge) {
      setStatus("PySide 未接続");
      return;
    }

    bridge.request_stop();
    setStatus("停止要求送信");
  });

  refreshTemplatesButton?.addEventListener("click", async () => {
    await refreshTemplateList();
  });
}

function setupBridge() {
  return new Promise((resolve) => {
    if (!window.qt || !window.QWebChannel) {
      setStatus("qt object not found");
      resolve();
      return;
    }

    new QWebChannel(qt.webChannelTransport, (channel) => {
      bridge = channel.objects.visualMacroBridge;

      if (bridge && bridge.ui_message) {
        bridge.ui_message.connect((message) => {
          setStatus(message);
        });
      }
      if (bridge && bridge.highlight_block_requested) {
        bridge.highlight_block_requested.connect((blockId) => {
          highlightExecutionBlock(blockId);
        });
      }

      if (bridge && bridge.clear_block_highlight_requested) {
        bridge.clear_block_highlight_requested.connect(() => {
          clearExecutionBlockHighlight();
        });
      }

      notifyDocumentState();
      setStatus("PySide 接続完了");
      resolve();
    });
  });
}

window.collectVisualMacroDocumentJson = function () {
  if (!workspace) {
    return "";
  }
  return JSON.stringify(buildVisualMacroDocumentWithMetadata(), null, 2);
};

window.markVisualMacroDocumentSaved = function (relativePath) {
  const normalizedPath =
    typeof relativePath === "string" ? relativePath : currentDocumentPath;
  markCurrentDocumentAsClean(normalizedPath);
  return true;
};

window.addEventListener("DOMContentLoaded", async () => {
  try {
    await setupBridge();
    setupButtons();
    setupMetadataInputs();
    setupRecentFilesDropdown();
    setupRoiModal();
    await initializeBlockly();

    if (bridge) {
      await refreshTemplateList();
    }

    refreshRecentFilesUi();
    updateEditorCaption();
  } catch (error) {
    console.error("[VisualMacro] Initialization failed:", error);
    setStatus(`初期化失敗: ${error.message}`);
  }
});

window.openVisualMacroDocumentByPath = function (relativePath) {
  (async () => {
    try {
      await openDocumentByPath(relativePath, {
        confirmDiscard: true,
        updateRecent: true,
      });
    } catch (error) {
      console.error("[VisualMacro] Open from Python failed:", error);
      setStatus(`読込失敗: ${error.message}`);
    }
  })();

  // Python 側には「要求は受け付けた」とだけ返す
  return true;
};

window.createNewVisualMacroDocument = function () {
  if (!workspace) {
    return false;
  }

  if (!confirmDiscardIfNeeded()) {
    return false;
  }

  suppressDirtyTracking = true;
  try {
    clearMetadataUi();
    workspace.clear();
    refreshProgramJson();
    setStatus("新規作成しました");
  } catch (error) {
    console.error("[VisualMacro] New workspace failed:", error);
    setStatus(`新規作成失敗: ${error.message}`);
    return false;
  } finally {
    window.setTimeout(() => {
      try {
        markCurrentDocumentAsClean("");
      } finally {
        suppressDirtyTracking = false;
      }
    }, 0);
  }

  return true;
};

// ==================================================================
// Template Preview (sidebar)
// ==================================================================

/**
 * Update the template preview image in the sidebar based on the
 * currently selected block's TEMPLATE field.
 */
function updateTemplatePreview() {
  const previewImg = document.getElementById("template-preview-img");
  const placeholder = document.getElementById("template-preview-placeholder");
  const roiBtn = document.getElementById("roi-select-btn");

  if (!previewImg || !placeholder) return;

  const templatePath = getSelectedTemplatePath(workspace);

  if (!templatePath) {
    previewImg.style.display = "none";
    previewImg.removeAttribute("src");
    placeholder.textContent =
      "画像ブロックを選択するとプレビューが表示されます";
    placeholder.style.display = "";
    if (roiBtn) roiBtn.disabled = true;
    // Don't clear _roiTargetBlockId here — keep last valid target
    return;
  }

  // Save the currently selected block ID for later ROI apply
  const currentSelected = Blockly.getSelected();
  if (currentSelected) {
    _roiTargetBlockId = currentSelected.id;
  }

  placeholder.textContent = "読み込み中...";
  placeholder.style.display = "";
  previewImg.style.display = "none";

  bridgeCall("get_template_preview_base64", [templatePath])
    .then((base64) => {
      if (!base64) {
        placeholder.textContent = "プレビューを取得できませんでした";
        placeholder.style.display = "";
        previewImg.style.display = "none";
        if (roiBtn) roiBtn.disabled = true;
        return;
      }

      // Set onload BEFORE setting src to reliably capture dimensions
      previewImg.onload = () => {
        _roiTemplateSize = {
          width: previewImg.naturalWidth,
          height: previewImg.naturalHeight,
        };
      };
      previewImg.src = "data:image/png;base64," + base64;
      previewImg.style.display = "block";
      placeholder.style.display = "none";
      if (roiBtn) roiBtn.disabled = false;

      // Fallback: if already loaded (cached data URL), read immediately
      if (previewImg.complete && previewImg.naturalWidth > 0) {
        _roiTemplateSize = {
          width: previewImg.naturalWidth,
          height: previewImg.naturalHeight,
        };
      }
    })
    .catch(() => {
      placeholder.textContent = "プレビューの取得に失敗しました";
      placeholder.style.display = "";
      previewImg.style.display = "none";
      if (roiBtn) roiBtn.disabled = true;
    });
}
