import {
  buildVisualMacroDocument,
  loadWorkspaceState,
  registerVisualMacroBlocks,
  serializeWorkspaceToProgram,
  updateTemplateDropdownOptions,
} from "./blocks.js";

let bridge = null;
let workspace = null;

let currentDocumentPath = "";
let isDocumentModified = false;
let suppressDirtyTracking = false;
let lastCleanDocumentSignature = "";

const RECENT_FILES_STORAGE_KEY = "visual_macro_recent_files";
const MAX_RECENT_FILES = 10;

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
