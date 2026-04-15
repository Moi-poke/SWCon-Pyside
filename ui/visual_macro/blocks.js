let currentTemplateOptions = [["(未設定)", ""]];

const INPUT_OPTIONS = [
  ["A", "A"],
  ["B", "B"],
  ["X", "X"],
  ["Y", "Y"],
  ["L", "L"],
  ["R", "R"],
  ["ZL", "ZL"],
  ["ZR", "ZR"],
  ["PLUS", "PLUS"],
  ["MINUS", "MINUS"],
  ["LS", "LCLICK"],
  ["RS", "RCLICK"],
  ["HOME", "HOME"],
  ["CAPTURE", "CAPTURE"],
  ["↑", "TOP"],
  ["↓", "BTM"],
  ["←", "LEFT"],
  ["→", "RIGHT"],
];

const OPTIONAL_INPUT_OPTIONS = [["(なし)", ""]].concat(INPUT_OPTIONS);

const STICK_OPTIONS = [
  ["左スティック", "LEFT_STICK"],
  ["右スティック", "RIGHT_STICK"],
];

const STICK_MODE_OPTIONS = [
  ["角度", "ANGLE"],
  ["8方向", "8WAY"],
];

const STICK_8WAY_OPTIONS = [
  ["→", "RIGHT"],
  ["↗", "UP_RIGHT"],
  ["↑", "UP"],
  ["↖", "UP_LEFT"],
  ["←", "LEFT"],
  ["↙", "DOWN_LEFT"],
  ["↓", "DOWN"],
  ["↘", "DOWN_RIGHT"],
];

function direction8ToAngle(directionName) {
  switch (directionName) {
    case "RIGHT":
      return 0;
    case "UP_RIGHT":
      return 45;
    case "UP":
      return 90;
    case "UP_LEFT":
      return 135;
    case "LEFT":
      return 180;
    case "DOWN_LEFT":
      return -135;
    case "DOWN":
      return -90;
    case "DOWN_RIGHT":
      return -45;
    default:
      return 0;
  }
}

export function registerVisualMacroBlocks() {
  Blockly.defineBlocksWithJsonArray([
    {
      type: "vm_press",
      message0: "%1 を押す 時間 %2 待機 %3",
      args0: [
        { type: "field_dropdown", name: "BUTTON", options: INPUT_OPTIONS },
        {
          type: "field_number",
          name: "DURATION",
          value: 0.1,
          min: 0,
          precision: 0.01,
        },
        {
          type: "field_number",
          name: "WAIT",
          value: 0.1,
          min: 0,
          precision: 0.01,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 210,
      tooltip: "単一入力を1回押します。",
      helpUrl: "",
    },
    {
      type: "vm_press_many",
      message0: "同時押し %1 %2 %3 %4",
      args0: [
        {
          type: "field_dropdown",
          name: "BUTTON1",
          options: OPTIONAL_INPUT_OPTIONS,
        },
        {
          type: "field_dropdown",
          name: "BUTTON2",
          options: OPTIONAL_INPUT_OPTIONS,
        },
        {
          type: "field_dropdown",
          name: "BUTTON3",
          options: OPTIONAL_INPUT_OPTIONS,
        },
        {
          type: "field_dropdown",
          name: "BUTTON4",
          options: OPTIONAL_INPUT_OPTIONS,
        },
      ],
      message1: "%1 %2 %3 %4",
      args1: [
        {
          type: "field_dropdown",
          name: "BUTTON5",
          options: OPTIONAL_INPUT_OPTIONS,
        },
        {
          type: "field_dropdown",
          name: "BUTTON6",
          options: OPTIONAL_INPUT_OPTIONS,
        },
        {
          type: "field_dropdown",
          name: "BUTTON7",
          options: OPTIONAL_INPUT_OPTIONS,
        },
        {
          type: "field_dropdown",
          name: "BUTTON8",
          options: OPTIONAL_INPUT_OPTIONS,
        },
      ],
      message2: "押下時間 %1 待機 %2",
      args2: [
        {
          type: "field_number",
          name: "DURATION",
          value: 0.1,
          min: 0,
          precision: 0.01,
        },
        {
          type: "field_number",
          name: "WAIT",
          value: 0.1,
          min: 0,
          precision: 0.01,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 215,
      tooltip: "最大8個までの入力を同時押しします。",
      helpUrl: "",
    },
    {
      type: "vm_mash",
      message0: "%1 を %2 回連打 1回の長さ %3 間隔 %4",
      args0: [
        { type: "field_dropdown", name: "BUTTON", options: INPUT_OPTIONS },
        { type: "field_number", name: "COUNT", value: 5, min: 0, precision: 1 },
        {
          type: "field_number",
          name: "DURATION",
          value: 0.05,
          min: 0,
          precision: 0.01,
        },
        {
          type: "field_number",
          name: "INTERVAL",
          value: 0.05,
          min: 0,
          precision: 0.01,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 220,
      tooltip: "同じ入力を指定回数連打します。",
      helpUrl: "",
    },
    {
      type: "vm_hold",
      message0: "%1 を長押しする 維持時間 %2",
      args0: [
        { type: "field_dropdown", name: "BUTTON", options: INPUT_OPTIONS },
        {
          type: "field_number",
          name: "DURATION",
          value: 0.5,
          min: 0,
          precision: 0.01,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 225,
      tooltip: "入力の長押しを開始します。",
      helpUrl: "",
    },
    {
      type: "vm_hold_end",
      message0: "%1 の長押しを解除する",
      args0: [
        { type: "field_dropdown", name: "BUTTON", options: INPUT_OPTIONS },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 228,
      tooltip: "入力の長押しを解除します。",
      helpUrl: "",
    },
    {
      type: "vm_wait",
      message0: "%1 秒待つ",
      args0: [
        {
          type: "field_number",
          name: "SECONDS",
          value: 1.0,
          min: 0,
          precision: 0.1,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 230,
      tooltip: "指定秒数待機します。",
      helpUrl: "",
    },
    {
      type: "vm_print",
      message0: "ログ表示 %1",
      args0: [
        {
          type: "field_input",
          name: "MESSAGE",
          text: "hello",
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 160,
      tooltip: "指定したメッセージをログに表示します。",
      helpUrl: "",
    },
    {
      type: "vm_if",
      message0: "もし %1 なら",
      args0: [{ type: "input_value", name: "CONDITION", check: "Boolean" }],
      message1: "%1",
      args1: [{ type: "input_statement", name: "THEN" }],
      message2: "でなければ",
      args2: [],
      message3: "%1",
      args3: [{ type: "input_statement", name: "ELSE" }],
      previousStatement: null,
      nextStatement: null,
      colour: 120,
      tooltip: "条件分岐を表します。",
      helpUrl: "",
    },
    {
      type: "vm_repeat",
      message0: "%1 回くりかえす",
      args0: [
        { type: "field_number", name: "COUNT", value: 3, min: 0, precision: 1 },
      ],
      message1: "%1",
      args1: [{ type: "input_statement", name: "BODY" }],
      previousStatement: null,
      nextStatement: null,
      colour: 65,
      tooltip: "固定回数のループです。",
      helpUrl: "",
    },
    {
      type: "vm_while_alive",
      message0: "停止されるまでくりかえす",
      message1: "%1",
      args1: [{ type: "input_statement", name: "BODY" }],
      previousStatement: null,
      nextStatement: null,
      colour: 70,
      tooltip: "停止要求が来るまで body を回し続けます。",
      helpUrl: "",
    },
    {
      type: "vm_finish",
      message0: "終了する",
      previousStatement: null,
      nextStatement: null,
      colour: 0,
      tooltip: "マクロ実行を終了します。",
      helpUrl: "",
    },
    {
      type: "vm_stick_move",
      message0: "スティックを倒す %1 方式 %2",
      args0: [
        { type: "field_dropdown", name: "STICK", options: STICK_OPTIONS },
        { type: "field_dropdown", name: "MODE", options: STICK_MODE_OPTIONS },
      ],
      message1: "角度 %1 8方向 %2",
      args1: [
        {
          type: "field_number",
          name: "ANGLE",
          value: 0,
          min: -180,
          max: 180,
          precision: 1,
        },
        { type: "field_dropdown", name: "DIR8", options: STICK_8WAY_OPTIONS },
      ],
      message2: "強さ %1 時間 %2 待機 %3",
      args2: [
        {
          type: "field_number",
          name: "RADIUS",
          value: 1.0,
          min: 0,
          max: 1,
          precision: 0.01,
        },
        {
          type: "field_number",
          name: "DURATION",
          value: 0.2,
          min: 0,
          precision: 0.01,
        },
        {
          type: "field_number",
          name: "WAIT",
          value: 0.1,
          min: 0,
          precision: 0.01,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 235,
      tooltip: "スティックを一時的に倒します。",
      helpUrl: "",
    },
    {
      type: "vm_stick_hold",
      message0: "スティックを倒したまま %1 方式 %2",
      args0: [
        { type: "field_dropdown", name: "STICK", options: STICK_OPTIONS },
        { type: "field_dropdown", name: "MODE", options: STICK_MODE_OPTIONS },
      ],
      message1: "角度 %1 8方向 %2",
      args1: [
        {
          type: "field_number",
          name: "ANGLE",
          value: 0,
          min: -180,
          max: 180,
          precision: 1,
        },
        { type: "field_dropdown", name: "DIR8", options: STICK_8WAY_OPTIONS },
      ],
      message2: "強さ %1 維持時間 %2",
      args2: [
        {
          type: "field_number",
          name: "RADIUS",
          value: 1.0,
          min: 0,
          max: 1,
          precision: 0.01,
        },
        {
          type: "field_number",
          name: "DURATION",
          value: 0.5,
          min: 0,
          precision: 0.01,
        },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 238,
      tooltip: "スティックを倒したままにします。",
      helpUrl: "",
    },
    {
      type: "vm_stick_release",
      message0: "スティックを戻す %1",
      args0: [
        { type: "field_dropdown", name: "STICK", options: STICK_OPTIONS },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: 240,
      tooltip: "スティックの保持を解除します。",
      helpUrl: "",
    },
  ]);

  Blockly.Blocks.vm_image_exists = {
    init() {
      this.appendDummyInput()
        .appendField("画像")
        .appendField(
          new Blockly.FieldDropdown(() => currentTemplateOptions),
          "TEMPLATE",
        )
        .appendField("が見つかる 閾値")
        .appendField(new Blockly.FieldNumber(0.85, 0, 1, 0.01), "THRESHOLD")
        .appendField("グレースケール")
        .appendField(new Blockly.FieldCheckbox("FALSE"), "USE_GRAY");

      this.setOutput(true, "Boolean");
      this.setColour(20);
      this.setTooltip("画像が見つかるかどうかを判定します。");
      this.setHelpUrl("");
    },
  };
  Blockly.Blocks.vm_wait_until_image = {
    init() {
      this.appendDummyInput()
        .appendField("画像")
        .appendField(
          new Blockly.FieldDropdown(() => currentTemplateOptions),
          "TEMPLATE",
        )
        .appendField("が見つかるまで待つ 閾値")
        .appendField(new Blockly.FieldNumber(0.85, 0, 1, 0.01), "THRESHOLD")
        .appendField("グレースケール")
        .appendField(new Blockly.FieldCheckbox("FALSE"), "USE_GRAY");

      this.appendDummyInput()
        .appendField("確認間隔")
        .appendField(
          new Blockly.FieldNumber(0.1, 0.01, undefined, 0.01),
          "POLL",
        )
        .appendField("タイムアウト(0=無制限)")
        .appendField(new Blockly.FieldNumber(0, 0, undefined, 0.1), "TIMEOUT");

      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(25);
      this.setTooltip("画像が見つかるまで待機します。");
      this.setHelpUrl("");
    },
  };

  Blockly.Blocks.vm_wait_until_not_image = {
    init() {
      this.appendDummyInput()
        .appendField("画像")
        .appendField(
          new Blockly.FieldDropdown(() => currentTemplateOptions),
          "TEMPLATE",
        )
        .appendField("が消えるまで待つ 閾値")
        .appendField(new Blockly.FieldNumber(0.85, 0, 1, 0.01), "THRESHOLD")
        .appendField("グレースケール")
        .appendField(new Blockly.FieldCheckbox("FALSE"), "USE_GRAY");

      this.appendDummyInput()
        .appendField("確認間隔")
        .appendField(
          new Blockly.FieldNumber(0.1, 0.01, undefined, 0.01),
          "POLL",
        )
        .appendField("タイムアウト(0=無制限)")
        .appendField(new Blockly.FieldNumber(0, 0, undefined, 0.1), "TIMEOUT");

      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(28);
      this.setTooltip("画像が見つからなくなるまで待機します。");
      this.setHelpUrl("");
    },
  };
}

export function updateTemplateDropdownOptions(templateEntries) {
  currentTemplateOptions =
    templateEntries.length > 0
      ? templateEntries.map((entry) => [
          entry.relative_path,
          entry.relative_path,
        ])
      : [["(未設定)", ""]];
}

function withBlockId(block, payload) {
  return {
    ...payload,
    block_id: block ? block.id : null,
  };
}

function collectManyButtons(block) {
  const buttons = [];
  for (const fieldName of [
    "BUTTON1",
    "BUTTON2",
    "BUTTON3",
    "BUTTON4",
    "BUTTON5",
    "BUTTON6",
    "BUTTON7",
    "BUTTON8",
  ]) {
    const value = block.getFieldValue(fieldName);
    if (value && value !== "") {
      buttons.push(value);
    }
  }
  return buttons;
}

function resolveStickAngle(block) {
  const mode = block.getFieldValue("MODE");
  if (mode === "8WAY") {
    return direction8ToAngle(block.getFieldValue("DIR8"));
  }
  return Number(block.getFieldValue("ANGLE"));
}

function serializeConditionBlock(block) {
  if (!block) {
    throw new Error("条件ブロックが未接続です。");
  }

  switch (block.type) {
    case "vm_image_exists":
      return withBlockId(block, {
        type: "image_exists",
        template: block.getFieldValue("TEMPLATE"),
        threshold: Number(block.getFieldValue("THRESHOLD")),
        use_gray: block.getFieldValue("USE_GRAY") === "TRUE",
      });

    default:
      throw new Error(`未対応の条件ブロックです: ${block.type}`);
  }
}

function serializeStatementBlock(block) {
  if (!block) {
    throw new Error("文ブロックが未接続です。");
  }

  switch (block.type) {
    case "vm_press":
      return withBlockId(block, {
        type: "press",
        button: block.getFieldValue("BUTTON"),
        duration: Number(block.getFieldValue("DURATION")),
        wait: Number(block.getFieldValue("WAIT")),
      });

    case "vm_press_many":
      return withBlockId(block, {
        type: "press_many",
        buttons: collectManyButtons(block),
        duration: Number(block.getFieldValue("DURATION")),
        wait: Number(block.getFieldValue("WAIT")),
      });

    case "vm_mash":
      return withBlockId(block, {
        type: "mash",
        button: block.getFieldValue("BUTTON"),
        count: Number(block.getFieldValue("COUNT")),
        duration: Number(block.getFieldValue("DURATION")),
        interval: Number(block.getFieldValue("INTERVAL")),
      });

    case "vm_hold":
      return withBlockId(block, {
        type: "hold",
        button: block.getFieldValue("BUTTON"),
        duration: Number(block.getFieldValue("DURATION")),
      });

    case "vm_hold_end":
      return withBlockId(block, {
        type: "hold_end",
        button: block.getFieldValue("BUTTON"),
      });

    case "vm_stick_move":
      return withBlockId(block, {
        type: "stick_move",
        stick: block.getFieldValue("STICK"),
        angle: resolveStickAngle(block),
        radius: Number(block.getFieldValue("RADIUS")),
        duration: Number(block.getFieldValue("DURATION")),
        wait: Number(block.getFieldValue("WAIT")),
      });

    case "vm_stick_hold":
      return withBlockId(block, {
        type: "stick_hold",
        stick: block.getFieldValue("STICK"),
        angle: resolveStickAngle(block),
        radius: Number(block.getFieldValue("RADIUS")),
        duration: Number(block.getFieldValue("DURATION")),
      });

    case "vm_stick_release":
      return withBlockId(block, {
        type: "stick_release",
        stick: block.getFieldValue("STICK"),
      });

    case "vm_wait":
      return withBlockId(block, {
        type: "wait",
        seconds: Number(block.getFieldValue("SECONDS")),
      });

    case "vm_print":
      return withBlockId(block, {
        type: "print",
        message: block.getFieldValue("MESSAGE"),
      });

    case "vm_if": {
      const conditionBlock = block.getInputTargetBlock("CONDITION");
      return withBlockId(block, {
        type: "if",
        condition: serializeConditionBlock(conditionBlock),
        then: serializeStatementInput(block, "THEN"),
        else: serializeStatementInput(block, "ELSE"),
      });
    }

    case "vm_repeat":
      return withBlockId(block, {
        type: "repeat",
        count: Number(block.getFieldValue("COUNT")),
        body: serializeStatementInput(block, "BODY"),
      });

    case "vm_finish":
      return withBlockId(block, {
        type: "finish",
      });

    case "vm_wait_until_image": {
      const timeout = Number(block.getFieldValue("TIMEOUT"));
      return withBlockId(block, {
        type: "wait_until_image",
        template: block.getFieldValue("TEMPLATE"),
        threshold: Number(block.getFieldValue("THRESHOLD")),
        use_gray: block.getFieldValue("USE_GRAY") === "TRUE",
        poll_interval: Number(block.getFieldValue("POLL")),
        timeout_seconds: timeout > 0 ? timeout : null,
      });
    }
    case "vm_wait_until_not_image": {
      const timeout = Number(block.getFieldValue("TIMEOUT"));
      return withBlockId(block, {
        type: "wait_until_not_image",
        template: block.getFieldValue("TEMPLATE"),
        threshold: Number(block.getFieldValue("THRESHOLD")),
        use_gray: block.getFieldValue("USE_GRAY") === "TRUE",
        poll_interval: Number(block.getFieldValue("POLL")),
        timeout_seconds: timeout > 0 ? timeout : null,
      });
    }
    case "vm_while_alive":
      return withBlockId(block, {
        type: "while_alive",
        body: serializeStatementInput(block, "BODY"),
      });

    default:
      throw new Error(`未対応の文ブロックです: ${block.type}`);
  }
}

function serializeStatementChain(firstBlock) {
  const children = [];
  let current = firstBlock;
  while (current) {
    children.push(serializeStatementBlock(current));
    current = current.getNextBlock();
  }
  return children;
}

function serializeStatementInput(block, inputName) {
  const firstBlock = block.getInputTargetBlock(inputName);
  return firstBlock ? serializeStatementChain(firstBlock) : [];
}

export function serializeWorkspaceToProgram(workspace) {
  if (!workspace) {
    return {
      version: "1.0",
      root: {
        type: "sequence",
        children: [],
        block_id: null,
      },
    };
  }

  const topBlocks = workspace
    .getTopBlocks(true)
    .filter((block) => block.outputConnection == null);

  const children = [];
  for (const block of topBlocks) {
    children.push(...serializeStatementChain(block));
  }

  return {
    version: "1.0",
    root: {
      type: "sequence",
      children,
      block_id: null,
    },
  };
}

export function serializeWorkspaceState(workspace) {
  if (!workspace) {
    return {};
  }

  if (Blockly.serialization?.workspaces?.save) {
    return Blockly.serialization.workspaces.save(workspace);
  }

  const xmlDom = Blockly.Xml.workspaceToDom(workspace);
  return {
    format: "xml_text",
    xml_text: Blockly.Xml.domToText(xmlDom),
  };
}

export function loadWorkspaceState(workspace, workspaceState) {
  if (!workspace) {
    throw new Error("workspace が未初期化です。");
  }

  workspace.clear();

  if (!workspaceState || Object.keys(workspaceState).length === 0) {
    return;
  }

  if (
    Blockly.serialization?.workspaces?.load &&
    workspaceState.format !== "xml_text"
  ) {
    Blockly.serialization.workspaces.load(workspaceState, workspace);
    return;
  }

  if (workspaceState.format === "xml_text") {
    const xmlDom = Blockly.Xml.textToDom(workspaceState.xml_text || "");
    Blockly.Xml.domToWorkspace(xmlDom, workspace);
    return;
  }

  throw new Error("未対応の workspace state 形式です。");
}

export function buildVisualMacroDocument(workspace) {
  return {
    format: "visual_macro_document",
    version: "1.0",
    metadata: {
      name: "",
      description: "",
      tags: [],
    },
    workspace: serializeWorkspaceState(workspace),
    program: serializeWorkspaceToProgram(workspace),
  };
}
