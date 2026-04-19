let currentTemplateOptions = [["(未設定)", ""]];

const INPUT_OPTIONS = [
  ["A","A"],["B","B"],["X","X"],["Y","Y"],["L","L"],["R","R"],["ZL","ZL"],["ZR","ZR"],
  ["PLUS","PLUS"],["MINUS","MINUS"],["LS","LCLICK"],["RS","RCLICK"],
  ["HOME","HOME"],["CAPTURE","CAPTURE"],
  ["\u2191","TOP"],["\u2193","BTM"],["\u2190","LEFT"],["\u2192","RIGHT"],
];
const STICK_OPTIONS = [["\u5de6\u30b9\u30c6\u30a3\u30c3\u30af","LEFT_STICK"],["\u53f3\u30b9\u30c6\u30a3\u30c3\u30af","RIGHT_STICK"]];
const STICK_MODE_OPTIONS = [["\u89d2\u5ea6","ANGLE"],["8\u65b9\u5411","8WAY"]];
const STICK_8WAY_OPTIONS = [
  ["\u2192","RIGHT"],["\u2197","UP_RIGHT"],["\u2191","UP"],["\u2196","UP_LEFT"],
  ["\u2190","LEFT"],["\u2199","DOWN_LEFT"],["\u2193","DOWN"],["\u2198","DOWN_RIGHT"],
];

function direction8ToAngle(d){switch(d){case"RIGHT":return 0;case"UP_RIGHT":return 45;case"UP":return 90;case"UP_LEFT":return 135;case"LEFT":return 180;case"DOWN_LEFT":return-135;case"DOWN":return-90;case"DOWN_RIGHT":return-45;default:return 0;}}

const _LOOP_BLOCK_TYPES = new Set(["vm_repeat","vm_while_alive","vm_while_condition","vm_while_image_exists","vm_while_not_image_exists","vm_for_range","vm_list_for_each"]);
function _isInsideLoop(block){let c=block.getSurroundParent();while(c){if(_LOOP_BLOCK_TYPES.has(c.type))return true;c=c.getSurroundParent();}return false;}
function _isInsideFunction(block){return block.getRootBlock()?.type==="vm_define_function";}

const _safeRegisterMutator=(name,mixin,helper,flyoutBlocks)=>{if(Blockly.Extensions.isRegistered(name))Blockly.Extensions.unregister(name);Blockly.Extensions.registerMutator(name,mixin,helper,flyoutBlocks);};

export function registerVisualMacroBlocks(){
  Blockly.Blocks.vm_function_def_container={init(){this.appendDummyInput().appendField("\u5f15\u6570");this.appendStatementInput("PARAMS");this.setColour(290);this.contextMenu=false;}};
  Blockly.Blocks.vm_function_def_param_item={init(){this.appendDummyInput().appendField("\u5f15\u6570");this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(290);this.contextMenu=false;}};
  Blockly.Blocks.vm_function_call_container={init(){this.appendDummyInput().appendField("\u5f15\u6570");this.appendStatementInput("ARGS");this.setColour(290);this.contextMenu=false;}};
  Blockly.Blocks.vm_function_call_arg_item={init(){this.appendDummyInput().appendField("\u5f15\u6570");this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(290);this.contextMenu=false;}};
  Blockly.Blocks.vm_list_create_with_container={init(){this.appendDummyInput().appendField("\u8981\u7d20");this.appendStatementInput("ITEMS");this.setColour(260);this.contextMenu=false;}};
  Blockly.Blocks.vm_list_create_with_item={init(){this.appendDummyInput().appendField("\u8981\u7d20");this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(260);this.contextMenu=false;}};
  Blockly.Blocks.vm_press_many_container={init(){this.appendDummyInput().appendField("\u30dc\u30bf\u30f3");this.appendStatementInput("BUTTONS");this.setColour(215);this.contextMenu=false;}};
  Blockly.Blocks.vm_press_many_button_item={init(){this.appendDummyInput().appendField("\u30dc\u30bf\u30f3");this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(215);this.contextMenu=false;}};

  _safeRegisterMutator("vm_define_function_mutator",{
    saveExtraState(){return{paramCount:this.paramCount_,paramNames:[...this.paramNames_]};},
    loadExtraState(s){this.paramCount_=s.paramCount||0;this.paramNames_=s.paramNames||[];this.updateShape_();},
    mutationToDom(){const m=Blockly.utils.xml.createElement("mutation");m.setAttribute("param_count",String(this.paramCount_));for(const n of this.paramNames_){const p=Blockly.utils.xml.createElement("param");p.setAttribute("name",n);m.appendChild(p);}return m;},
    domToMutation(x){this.paramCount_=parseInt(x.getAttribute("param_count")||"0",10);this.paramNames_=[];for(const c of x.childNodes){if(c.nodeName?.toLowerCase()==="param")this.paramNames_.push(c.getAttribute("name")||"");}this.updateShape_();},
    decompose(ws){const c=ws.newBlock("vm_function_def_container");c.initSvg();let cn=c.getInput("PARAMS").connection;for(let i=0;i<this.paramCount_;i++){const it=ws.newBlock("vm_function_def_param_item");it.initSvg();cn.connect(it.previousConnection);cn=it.nextConnection;}return c;},
    compose(cb){const old=[];for(let i=0;i<this.paramCount_;i++){const f=this.getField("PARAM_NAME_"+i);old.push(f?f.getValue():"arg"+i);}let cnt=0,it=cb.getInputTargetBlock("PARAMS");while(it){cnt++;it=it.getNextBlock();}const nm=[];for(let i=0;i<cnt;i++)nm.push(i<old.length?old[i]:"arg"+i);this.paramCount_=cnt;this.paramNames_=nm;this.updateShape_();},
    updateShape_(){for(let i=0;this.getInput("PARAM_"+i);i++)this.removeInput("PARAM_"+i);for(let i=0;i<this.paramCount_;i++){this.appendDummyInput("PARAM_"+i).appendField("  \u5f15\u6570"+(i+1)+":").appendField(new Blockly.FieldTextInput(this.paramNames_[i]||"arg"+i),"PARAM_NAME_"+i);}if(this.getInput("BODY"))this.moveInputBefore("BODY",null);},
  },function(){this.paramCount_=0;this.paramNames_=[];},["vm_function_def_param_item"]);

  _safeRegisterMutator("vm_call_function_mutator",{
    saveExtraState(){return{argCount:this.argCount_,argNames:[...this.argNames_]};},
    loadExtraState(s){this.argCount_=s.argCount||0;this.argNames_=s.argNames||[];this.updateShape_();},
    mutationToDom(){const m=Blockly.utils.xml.createElement("mutation");m.setAttribute("arg_count",String(this.argCount_));for(const n of this.argNames_){const a=Blockly.utils.xml.createElement("arg");a.setAttribute("name",n);m.appendChild(a);}return m;},
    domToMutation(x){this.argCount_=parseInt(x.getAttribute("arg_count")||"0",10);this.argNames_=[];for(const c of x.childNodes){if(c.nodeName?.toLowerCase()==="arg")this.argNames_.push(c.getAttribute("name")||"");}this.updateShape_();},
    decompose(ws){const c=ws.newBlock("vm_function_call_container");c.initSvg();let cn=c.getInput("ARGS").connection;for(let i=0;i<this.argCount_;i++){const it=ws.newBlock("vm_function_call_arg_item");it.initSvg();cn.connect(it.previousConnection);cn=it.nextConnection;}return c;},
    compose(cb){const old=[],oc=[];for(let i=0;i<this.argCount_;i++){const f=this.getField("ARG_NAME_"+i);old.push(f?f.getValue():"arg"+i);const inp=this.getInput("ARG_"+i);oc.push(inp&&inp.connection?inp.connection.targetConnection:null);}let cnt=0,it=cb.getInputTargetBlock("ARGS");while(it){cnt++;it=it.getNextBlock();}const nm=[];for(let i=0;i<cnt;i++)nm.push(i<old.length?old[i]:"arg"+i);this.argCount_=cnt;this.argNames_=nm;this.updateShape_();for(let i=0;i<cnt&&i<oc.length;i++){if(oc[i]){const inp=this.getInput("ARG_"+i);if(inp&&inp.connection)inp.connection.connect(oc[i]);}}},
    updateShape_(){for(let i=0;this.getInput("ARG_"+i);i++)this.removeInput("ARG_"+i);for(let i=0;i<this.argCount_;i++){this.appendValueInput("ARG_"+i).appendField(new Blockly.FieldTextInput(this.argNames_[i]||"arg"+i),"ARG_NAME_"+i).appendField("=");}},
  },function(){this.argCount_=0;this.argNames_=[];},["vm_function_call_arg_item"]);

  _safeRegisterMutator("vm_list_create_with_mutator",{
    saveExtraState(){return{itemCount:this.itemCount_};},
    loadExtraState(s){this.itemCount_=s.itemCount||0;this.updateShape_();},
    mutationToDom(){const m=Blockly.utils.xml.createElement("mutation");m.setAttribute("item_count",String(this.itemCount_));return m;},
    domToMutation(x){this.itemCount_=parseInt(x.getAttribute("item_count")||"0",10);this.updateShape_();},
    decompose(ws){const c=ws.newBlock("vm_list_create_with_container");c.initSvg();let cn=c.getInput("ITEMS").connection;for(let i=0;i<this.itemCount_;i++){const it=ws.newBlock("vm_list_create_with_item");it.initSvg();cn.connect(it.previousConnection);cn=it.nextConnection;}return c;},
    compose(cb){const oc=[];for(let i=0;i<this.itemCount_;i++){const inp=this.getInput("VALUE_"+i);oc.push(inp&&inp.connection?inp.connection.targetConnection:null);}let cnt=0,it=cb.getInputTargetBlock("ITEMS");while(it){cnt++;it=it.getNextBlock();}this.itemCount_=cnt;this.updateShape_();for(let i=0;i<cnt&&i<oc.length;i++){if(oc[i]){const inp=this.getInput("VALUE_"+i);if(inp&&inp.connection)inp.connection.connect(oc[i]);}}},
    updateShape_(){for(let i=0;this.getInput("VALUE_"+i);i++)this.removeInput("VALUE_"+i);for(let i=0;i<this.itemCount_;i++){this.appendValueInput("VALUE_"+i).appendField("\u8981\u7d20"+(i+1));}},
  },function(){this.itemCount_=2;this.updateShape_();},["vm_list_create_with_item"]);

  _safeRegisterMutator("vm_press_many_mutator",{
    saveExtraState(){return{buttonCount:this.buttonCount_};},
    loadExtraState(s){this.buttonCount_=s.buttonCount||0;this.updateShape_();},
    mutationToDom(){const m=Blockly.utils.xml.createElement("mutation");m.setAttribute("button_count",String(this.buttonCount_));return m;},
    domToMutation(x){this.buttonCount_=parseInt(x.getAttribute("button_count")||"0",10);this.updateShape_();},
    decompose(ws){const c=ws.newBlock("vm_press_many_container");c.initSvg();let cn=c.getInput("BUTTONS").connection;for(let i=0;i<this.buttonCount_;i++){const it=ws.newBlock("vm_press_many_button_item");it.initSvg();cn.connect(it.previousConnection);cn=it.nextConnection;}return c;},
    compose(cb){const ov=[];for(let i=0;i<this.buttonCount_;i++){const f=this.getField("BUTTON_"+i);ov.push(f?f.getValue():"A");}let cnt=0,it=cb.getInputTargetBlock("BUTTONS");while(it){cnt++;it=it.getNextBlock();}if(cnt<1)cnt=1;this.buttonCount_=cnt;this.updateShape_();for(let i=0;i<cnt&&i<ov.length;i++){const f=this.getField("BUTTON_"+i);if(f)f.setValue(ov[i]);}},
    updateShape_(){for(let i=0;this.getInput("BUTTON_"+i);i++)this.removeInput("BUTTON_"+i);for(let i=0;i<this.buttonCount_;i++){this.appendDummyInput("BUTTON_"+i).appendField("  \u30dc\u30bf\u30f3"+(i+1)).appendField(new Blockly.FieldDropdown(INPUT_OPTIONS),"BUTTON_"+i);}if(this.getInput("TIMING"))this.moveInputBefore("TIMING",null);},
  },function(){this.buttonCount_=2;this.appendDummyInput("TIMING").appendField("\u62bc\u4e0b\u6642\u9593").appendField(new Blockly.FieldNumber(0.1,0,undefined,0.01),"DURATION").appendField("\u5f85\u6a5f").appendField(new Blockly.FieldNumber(0.1,0,undefined,0.01),"WAIT");this.updateShape_();},["vm_press_many_button_item"]);

  Blockly.defineBlocksWithJsonArray([
    {type:"vm_press",message0:"%1 \u3092\u62bc\u3059 \u6642\u9593 %2 \u5f85\u6a5f %3",args0:[{type:"field_dropdown",name:"BUTTON",options:INPUT_OPTIONS},{type:"field_number",name:"DURATION",value:0.1,min:0,precision:0.01},{type:"field_number",name:"WAIT",value:0.1,min:0,precision:0.01}],previousStatement:null,nextStatement:null,colour:210,tooltip:"\u5358\u4e00\u5165\u529b\u30921\u56de\u62bc\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_press_many",message0:"\u540c\u6642\u62bc\u3057",previousStatement:null,nextStatement:null,colour:215,tooltip:"\u30dc\u30bf\u30f3\u306e\u540c\u6642\u62bc\u3057\u3067\u3059\u3002\u2699\u3067\u30dc\u30bf\u30f3\u6570\u3092\u5909\u66f4\u3002",helpUrl:"",mutator:"vm_press_many_mutator"},
    {type:"vm_mash",message0:"%1 \u3092 %2 \u56de\u9023\u6253 1\u56de\u306e\u9577\u3055 %3 \u9593\u9694 %4",args0:[{type:"field_dropdown",name:"BUTTON",options:INPUT_OPTIONS},{type:"field_number",name:"COUNT",value:5,min:0,precision:1},{type:"field_number",name:"DURATION",value:0.05,min:0,precision:0.01},{type:"field_number",name:"INTERVAL",value:0.05,min:0,precision:0.01}],previousStatement:null,nextStatement:null,colour:220,tooltip:"\u540c\u3058\u5165\u529b\u3092\u6307\u5b9a\u56de\u6570\u9023\u6253\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_hold",message0:"%1 \u3092\u9577\u62bc\u3057\u3059\u308b \u7dad\u6301\u6642\u9593 %2",args0:[{type:"field_dropdown",name:"BUTTON",options:INPUT_OPTIONS},{type:"field_number",name:"DURATION",value:0.5,min:0,precision:0.01}],previousStatement:null,nextStatement:null,colour:225,tooltip:"\u5165\u529b\u306e\u9577\u62bc\u3057\u3092\u958b\u59cb\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_hold_end",message0:"%1 \u306e\u9577\u62bc\u3057\u3092\u89e3\u9664\u3059\u308b",args0:[{type:"field_dropdown",name:"BUTTON",options:INPUT_OPTIONS}],previousStatement:null,nextStatement:null,colour:228,tooltip:"\u5165\u529b\u306e\u9577\u62bc\u3057\u3092\u89e3\u9664\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_wait",message0:"%1 \u79d2\u5f85\u3064",args0:[{type:"field_number",name:"SECONDS",value:1.0,min:0,precision:0.1}],previousStatement:null,nextStatement:null,colour:230,tooltip:"\u6307\u5b9a\u79d2\u6570\u5f85\u6a5f\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_print",message0:"\u30ed\u30b0\u8868\u793a %1",args0:[{type:"field_input",name:"MESSAGE",text:"hello"}],previousStatement:null,nextStatement:null,colour:160,tooltip:"\u30e1\u30c3\u30bb\u30fc\u30b8\u3092\u30ed\u30b0\u306b\u8868\u793a\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_print_value",message0:"\u30ed\u30b0\u8868\u793a(\u5024) %1",args0:[{type:"input_value",name:"VALUE"}],previousStatement:null,nextStatement:null,colour:160,tooltip:"\u5024\u30d6\u30ed\u30c3\u30af\u306e\u7d50\u679c\u3092\u30ed\u30b0\u306b\u8868\u793a\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_comment",message0:"\uD83D\uDCAC %1",args0:[{type:"field_input",name:"MESSAGE",text:"\u30e1\u30e2"}],previousStatement:null,nextStatement:null,colour:180,tooltip:"\u30b3\u30e1\u30f3\u30c8\u3067\u3059\u3002\u5b9f\u884c\u306b\u306f\u5f71\u97ff\u3057\u307e\u305b\u3093\u3002",helpUrl:""},
    {type:"vm_finish",message0:"\u7d42\u4e86\u3059\u308b",previousStatement:null,nextStatement:null,colour:0,tooltip:"\u30de\u30af\u30ed\u5b9f\u884c\u3092\u7d42\u4e86\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_if",message0:"\u3082\u3057 %1 \u306a\u3089",args0:[{type:"input_value",name:"CONDITION",check:"Boolean"}],message1:"%1",args1:[{type:"input_statement",name:"THEN"}],message2:"\u3067\u306a\u3051\u308c\u3070",args2:[],message3:"%1",args3:[{type:"input_statement",name:"ELSE"}],previousStatement:null,nextStatement:null,colour:120,tooltip:"\u6761\u4ef6\u5206\u5c90\u3092\u8868\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_repeat",message0:"%1 \u56de\u304f\u308a\u304b\u3048\u3059",args0:[{type:"field_number",name:"COUNT",value:3,min:0,precision:1}],message1:"%1",args1:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:65,tooltip:"\u56fa\u5b9a\u56de\u6570\u306e\u30eb\u30fc\u30d7\u3067\u3059\u3002",helpUrl:""},
    {type:"vm_while_alive",message0:"\u505c\u6b62\u3055\u308c\u308b\u307e\u3067\u304f\u308a\u304b\u3048\u3059",message1:"%1",args1:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:70,tooltip:"\u505c\u6b62\u8981\u6c42\u304c\u6765\u308b\u307e\u3067\u56de\u3057\u7d9a\u3051\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_while_condition",message0:"%1 \u306e\u9593\u304f\u308a\u304b\u3048\u3059",args0:[{type:"input_value",name:"CONDITION",check:"Boolean"}],message1:"%1",args1:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:65,tooltip:"\u6761\u4ef6\u304c\u771f\u306e\u9593\u7e70\u308a\u8fd4\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_for_range",message0:"\u5909\u6570 %1 : %2 \u304b\u3089 %3 \u307e\u3067 \u304f\u308a\u304b\u3048\u3059 \u30b9\u30c6\u30c3\u30d7 %4",args0:[{type:"field_input",name:"VAR_NAME",text:"i"},{type:"field_number",name:"FROM",value:0,precision:1},{type:"field_number",name:"TO",value:9,precision:1},{type:"field_number",name:"STEP",value:1,precision:1}],message1:"%1",args1:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:65,tooltip:"\u5909\u6570\u3092\u30ab\u30a6\u30f3\u30bf\u3068\u3057\u3066\u6307\u5b9a\u7bc4\u56f2\u3067\u30eb\u30fc\u30d7\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_list_for_each",message0:"\u5909\u6570 %1 : %2 \u306e\u5404\u8981\u7d20\u3067\u304f\u308a\u304b\u3048\u3059",args0:[{type:"field_input",name:"VAR_NAME",text:"item"},{type:"input_value",name:"LIST"}],message1:"%1",args1:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:65,tooltip:"\u30ea\u30b9\u30c8\u306e\u5404\u8981\u7d20\u3067\u30eb\u30fc\u30d7\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_while_image_exists",message0:"\u753b\u50cf %1 \u304c\u898b\u3064\u304b\u308b\u9593\u304f\u308a\u304b\u3048\u3059 \u95be\u5024 %2 \u30b0\u30ec\u30fc\u30b9\u30b1\u30fc\u30eb %3",args0:[{type:"field_dropdown",name:"TEMPLATE",options:()=>currentTemplateOptions},{type:"field_number",name:"THRESHOLD",value:0.85,min:0,max:1,precision:0.01},{type:"field_checkbox",name:"USE_GRAY",checked:false}],message1:"ROI(0=\u5168\u4f53) %1 , %2 , %3 , %4",args1:[{type:"field_number",name:"TRIM_X1",value:0,min:0,precision:1},{type:"field_number",name:"TRIM_Y1",value:0,min:0,precision:1},{type:"field_number",name:"TRIM_X2",value:0,min:0,precision:1},{type:"field_number",name:"TRIM_Y2",value:0,min:0,precision:1}],message2:"\u78ba\u8a8d\u9593\u9694 %1 \u30bf\u30a4\u30e0\u30a2\u30a6\u30c8(0=\u7121\u5236\u9650) %2",args2:[{type:"field_number",name:"POLL",value:0.1,min:0.01,precision:0.01},{type:"field_number",name:"TIMEOUT",value:0,min:0,precision:0.1}],message3:"%1",args3:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:35,tooltip:"\u753b\u50cf\u304c\u898b\u3064\u304b\u308b\u9593\u7e70\u308a\u8fd4\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_while_not_image_exists",message0:"\u753b\u50cf %1 \u304c\u898b\u3064\u304b\u3089\u306a\u3044\u9593\u304f\u308a\u304b\u3048\u3059 \u95be\u5024 %2 \u30b0\u30ec\u30fc\u30b9\u30b1\u30fc\u30eb %3",args0:[{type:"field_dropdown",name:"TEMPLATE",options:()=>currentTemplateOptions},{type:"field_number",name:"THRESHOLD",value:0.85,min:0,max:1,precision:0.01},{type:"field_checkbox",name:"USE_GRAY",checked:false}],message1:"ROI(0=\u5168\u4f53) %1 , %2 , %3 , %4",args1:[{type:"field_number",name:"TRIM_X1",value:0,min:0,precision:1},{type:"field_number",name:"TRIM_Y1",value:0,min:0,precision:1},{type:"field_number",name:"TRIM_X2",value:0,min:0,precision:1},{type:"field_number",name:"TRIM_Y2",value:0,min:0,precision:1}],message2:"\u78ba\u8a8d\u9593\u9694 %1 \u30bf\u30a4\u30e0\u30a2\u30a6\u30c8(0=\u7121\u5236\u9650) %2",args2:[{type:"field_number",name:"POLL",value:0.1,min:0.01,precision:0.01},{type:"field_number",name:"TIMEOUT",value:0,min:0,precision:0.1}],message3:"%1",args3:[{type:"input_statement",name:"BODY"}],previousStatement:null,nextStatement:null,colour:38,tooltip:"\u753b\u50cf\u304c\u898b\u3064\u304b\u3089\u306a\u3044\u9593\u7e70\u308a\u8fd4\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_stick_move",message0:"\u30b9\u30c6\u30a3\u30c3\u30af\u3092\u5012\u3059 %1 \u65b9\u5f0f %2",args0:[{type:"field_dropdown",name:"STICK",options:STICK_OPTIONS},{type:"field_dropdown",name:"MODE",options:STICK_MODE_OPTIONS}],message1:"\u89d2\u5ea6 %1 8\u65b9\u5411 %2",args1:[{type:"field_number",name:"ANGLE",value:0,min:-180,max:180,precision:1},{type:"field_dropdown",name:"DIR8",options:STICK_8WAY_OPTIONS}],message2:"\u5f37\u3055 %1 \u6642\u9593 %2 \u5f85\u6a5f %3",args2:[{type:"field_number",name:"RADIUS",value:1.0,min:0,max:1,precision:0.01},{type:"field_number",name:"DURATION",value:0.2,min:0,precision:0.01},{type:"field_number",name:"WAIT",value:0.1,min:0,precision:0.01}],previousStatement:null,nextStatement:null,colour:235,tooltip:"\u30b9\u30c6\u30a3\u30c3\u30af\u3092\u4e00\u6642\u7684\u306b\u5012\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_stick_hold",message0:"\u30b9\u30c6\u30a3\u30c3\u30af\u3092\u5012\u3057\u305f\u307e\u307e %1 \u65b9\u5f0f %2",args0:[{type:"field_dropdown",name:"STICK",options:STICK_OPTIONS},{type:"field_dropdown",name:"MODE",options:STICK_MODE_OPTIONS}],message1:"\u89d2\u5ea6 %1 8\u65b9\u5411 %2",args1:[{type:"field_number",name:"ANGLE",value:0,min:-180,max:180,precision:1},{type:"field_dropdown",name:"DIR8",options:STICK_8WAY_OPTIONS}],message2:"\u5f37\u3055 %1 \u7dad\u6301\u6642\u9593 %2",args2:[{type:"field_number",name:"RADIUS",value:1.0,min:0,max:1,precision:0.01},{type:"field_number",name:"DURATION",value:0.5,min:0,precision:0.01}],previousStatement:null,nextStatement:null,colour:238,tooltip:"\u30b9\u30c6\u30a3\u30c3\u30af\u3092\u5012\u3057\u305f\u307e\u307e\u306b\u3057\u307e\u3059\u3002",helpUrl:""},
    {type:"vm_stick_release",message0:"\u30b9\u30c6\u30a3\u30c3\u30af\u3092\u623b\u3059 %1",args0:[{type:"field_dropdown",name:"STICK",options:STICK_OPTIONS}],previousStatement:null,nextStatement:null,colour:240,tooltip:"\u30b9\u30c6\u30a3\u30c3\u30af\u306e\u4fdd\u6301\u3092\u89e3\u9664\u3057\u307e\u3059\u3002",helpUrl:""},
    // 変数
    {type:"vm_set_variable",message0:"変数 %1 を %2 にする",args0:[{type:"field_input",name:"VAR_NAME",text:"i"},{type:"input_value",name:"VALUE"}],inputsInline:true,previousStatement:null,nextStatement:null,colour:330,tooltip:"変数に値をセットします。",helpUrl:""},
    {type:"vm_get_variable",message0:"変数 %1",args0:[{type:"field_input",name:"VAR_NAME",text:"i"}],output:null,colour:330,tooltip:"変数の値を取得します。",helpUrl:""},
    {type:"vm_change_variable",message0:"変数 %1 を %2 だけ変える",args0:[{type:"field_input",name:"VAR_NAME",text:"i"},{type:"input_value",name:"DELTA",check:"Number"}],inputsInline:true,previousStatement:null,nextStatement:null,colour:330,tooltip:"変数の値を指定量だけ変化させます。",helpUrl:""},
    // 論理
    {type:"vm_compare",message0:"%1 %2 %3",args0:[{type:"input_value",name:"LEFT"},{type:"field_dropdown",name:"OP",options:[["=","EQ"],["≠","NEQ"],["<","LT"],[">","GT"],["≤","LTE"],["≥","GTE"]]},{type:"input_value",name:"RIGHT"}],inputsInline:true,output:"Boolean",colour:210,tooltip:"2つの値を比較します。",helpUrl:""},
    {type:"vm_logic_operation",message0:"%1 %2 %3",args0:[{type:"input_value",name:"LEFT",check:"Boolean"},{type:"field_dropdown",name:"OP",options:[["かつ","AND"],["または","OR"]]},{type:"input_value",name:"RIGHT",check:"Boolean"}],inputsInline:true,output:"Boolean",colour:210,tooltip:"論理演算を行います。",helpUrl:""},
    {type:"vm_logic_not",message0:"%1 でない",args0:[{type:"input_value",name:"VALUE",check:"Boolean"}],output:"Boolean",colour:210,tooltip:"論理否定を行います。",helpUrl:""},
    {type:"vm_boolean",message0:"%1",args0:[{type:"field_dropdown",name:"BOOL",options:[["真","TRUE"],["偽","FALSE"]]}],output:"Boolean",colour:210,tooltip:"真偽値リテラルです。",helpUrl:""},
    {type:"vm_ternary",message0:"もし %1 なら %2 でなければ %3",args0:[{type:"input_value",name:"CONDITION",check:"Boolean"},{type:"input_value",name:"TRUE_VALUE"},{type:"input_value",name:"FALSE_VALUE"}],inputsInline:true,output:null,colour:210,tooltip:"条件に応じて値を返します。",helpUrl:""},
    // 数値
    {type:"vm_number",message0:"%1",args0:[{type:"field_number",name:"NUM",value:0,precision:0.01}],output:"Number",colour:230,tooltip:"数値リテラルです。",helpUrl:""},
    {type:"vm_arithmetic",message0:"%1 %2 %3",args0:[{type:"input_value",name:"LEFT",check:"Number"},{type:"field_dropdown",name:"OP",options:[["+","ADD"],["\u2212","SUB"],["\u00d7","MUL"],["\u00f7","DIV"],["%","MOD"]]},{type:"input_value",name:"RIGHT",check:"Number"}],inputsInline:true,output:"Number",colour:230,tooltip:"四則演算を行います。",helpUrl:""},
    {type:"vm_random_int",message0:"%1 から %2 の乱数",args0:[{type:"field_number",name:"MIN",value:1,precision:1},{type:"field_number",name:"MAX",value:10,precision:1}],output:"Number",colour:230,tooltip:"指定範囲の整数乱数を生成します。",helpUrl:""},
    {type:"vm_random_float",message0:"%1 から %2 の小数乱数",args0:[{type:"field_number",name:"MIN",value:0.0,precision:0.01},{type:"field_number",name:"MAX",value:1.0,precision:0.01}],output:"Number",colour:230,tooltip:"指定範囲のランダム小数を返します。",helpUrl:""},
    {type:"vm_math_single",message0:"%1 %2",args0:[{type:"field_dropdown",name:"OP",options:[["abs","ABS"],["round","ROUND"],["floor","FLOOR"],["ceil","CEIL"]]},{type:"input_value",name:"VALUE",check:"Number"}],output:"Number",colour:230,tooltip:"数学関数を適用します。",helpUrl:""},
    {type:"vm_math_minmax",message0:"%1 ( %2 , %3 )",args0:[{type:"field_dropdown",name:"OP",options:[["min","MIN"],["max","MAX"]]},{type:"input_value",name:"LEFT",check:"Number"},{type:"input_value",name:"RIGHT",check:"Number"}],inputsInline:true,output:"Number",colour:230,tooltip:"2値の最小/最大を返します。",helpUrl:""},
    {type:"vm_to_number",message0:"数値に変換 %1",args0:[{type:"input_value",name:"VALUE"}],output:"Number",colour:230,tooltip:"値を数値に変換します。",helpUrl:""},
    // テキスト
    {type:"vm_text",message0:'" %1 "',args0:[{type:"field_input",name:"TEXT",text:""}],output:"String",colour:160,tooltip:"テキストリテラルです。",helpUrl:""},
    {type:"vm_text_join",message0:"%1 と %2 を結合",args0:[{type:"input_value",name:"LEFT"},{type:"input_value",name:"RIGHT"}],inputsInline:true,output:"String",colour:160,tooltip:"2つの値をテキストとして結合します。",helpUrl:""},
    {type:"vm_to_text",message0:"テキストに変換 %1",args0:[{type:"input_value",name:"VALUE"}],output:"String",colour:160,tooltip:"値をテキストに変換します。",helpUrl:""},
    {type:"vm_text_length",message0:"%1 の文字数",args0:[{type:"input_value",name:"VALUE"}],output:"Number",colour:160,tooltip:"テキストの文字数を返します。",helpUrl:""},
    {type:"vm_text_contains",message0:"%1 に %2 が含まれる",args0:[{type:"input_value",name:"TEXT"},{type:"input_value",name:"SEARCH"}],inputsInline:true,output:"Boolean",colour:160,tooltip:"テキストに検索文字が含まれるか判定します。",helpUrl:""},
    {type:"vm_text_substring",message0:"%1 の %2 文字目から %3 文字",args0:[{type:"input_value",name:"TEXT"},{type:"input_value",name:"START",check:"Number"},{type:"input_value",name:"LENGTH",check:"Number"}],inputsInline:true,output:"String",colour:160,tooltip:"テキストの一部を切り出します（0始まり）。",helpUrl:""},
    // リスト
    {type:"vm_list_create_empty",message0:"空のリスト",output:"Array",colour:260,tooltip:"空のリストを作成します。",helpUrl:""},
    {type:"vm_list_create_with",message0:"リストを作成",output:"Array",colour:260,tooltip:"要素を指定してリストを作成します。⚙で要素数を変更。",helpUrl:"",mutator:"vm_list_create_with_mutator"},
    {type:"vm_list_length",message0:"%1 の長さ",args0:[{type:"input_value",name:"LIST"}],output:"Number",colour:260,tooltip:"リストの要素数を返します。",helpUrl:""},
    {type:"vm_list_get",message0:"%1 の %2 番目",args0:[{type:"input_value",name:"LIST"},{type:"input_value",name:"INDEX",check:"Number"}],inputsInline:true,output:null,colour:260,tooltip:"リストの指定位置の要素を取得します（0始まり）。",helpUrl:""},
    {type:"vm_list_set",message0:"変数 %1 の %2 番目を %3 にする",args0:[{type:"field_input",name:"VAR_NAME",text:"myList"},{type:"input_value",name:"INDEX",check:"Number"},{type:"input_value",name:"VALUE"}],inputsInline:true,previousStatement:null,nextStatement:null,colour:260,tooltip:"リストの指定位置の要素を変更します（0始まり）。",helpUrl:""},
    {type:"vm_list_append",message0:"変数 %1 に %2 を追加",args0:[{type:"field_input",name:"VAR_NAME",text:"myList"},{type:"input_value",name:"VALUE"}],inputsInline:true,previousStatement:null,nextStatement:null,colour:260,tooltip:"リストの末尾に要素を追加します。",helpUrl:""},
    // 関数
    {type:"vm_define_function",message0:"関数を定義 %1",args0:[{type:"field_input",name:"FUNC_NAME",text:"myFunc"}],message1:"実行内容 %1",args1:[{type:"input_statement",name:"BODY"}],colour:290,tooltip:"関数を定義します。⚙で引数を追加。",helpUrl:"",mutator:"vm_define_function_mutator"},
    {type:"vm_call_function",message0:"関数 %1 を呼び出す",args0:[{type:"field_input",name:"FUNC_NAME",text:"myFunc"}],previousStatement:null,nextStatement:null,colour:290,tooltip:"定義済み関数を呼び出します。",helpUrl:"",mutator:"vm_call_function_mutator"},
    {type:"vm_call_function_value",message0:"関数 %1 の戻り値",args0:[{type:"field_input",name:"FUNC_NAME",text:"myFunc"}],output:null,colour:290,tooltip:"関数を呼び出し、戻り値を返します。",helpUrl:"",mutator:"vm_call_function_mutator"},
  ]);

  // ── 手動定義: 画像認識 (with ROI) ──
  Blockly.Blocks.vm_image_exists={init(){this.appendDummyInput().appendField("画像").appendField(new Blockly.FieldDropdown(()=>currentTemplateOptions),"TEMPLATE").appendField("が見つかる 閾値").appendField(new Blockly.FieldNumber(0.85,0,1,0.01),"THRESHOLD").appendField("グレースケール").appendField(new Blockly.FieldCheckbox("FALSE"),"USE_GRAY");this.appendDummyInput().appendField("ROI(0=全体)").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_X1").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_Y1").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_X2").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_Y2");this.setOutput(true,"Boolean");this.setColour(20);this.setTooltip("画像が見つかるかどうかを判定します。");this.setHelpUrl("");}};
  Blockly.Blocks.vm_wait_until_image={init(){this.appendDummyInput().appendField("画像").appendField(new Blockly.FieldDropdown(()=>currentTemplateOptions),"TEMPLATE").appendField("が見つかるまで待つ 閾値").appendField(new Blockly.FieldNumber(0.85,0,1,0.01),"THRESHOLD").appendField("グレースケール").appendField(new Blockly.FieldCheckbox("FALSE"),"USE_GRAY");this.appendDummyInput().appendField("ROI(0=全体)").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_X1").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_Y1").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_X2").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_Y2");this.appendDummyInput().appendField("確認間隔").appendField(new Blockly.FieldNumber(0.1,0.01,undefined,0.01),"POLL").appendField("タイムアウト(0=無制限)").appendField(new Blockly.FieldNumber(0,0,undefined,0.1),"TIMEOUT");this.setPreviousStatement(true,null);this.setNextStatement(true,null);this.setColour(25);this.setTooltip("画像が見つかるまで待機します。");this.setHelpUrl("");}};
  Blockly.Blocks.vm_wait_until_not_image={init(){this.appendDummyInput().appendField("画像").appendField(new Blockly.FieldDropdown(()=>currentTemplateOptions),"TEMPLATE").appendField("が消えるまで待つ 閾値").appendField(new Blockly.FieldNumber(0.85,0,1,0.01),"THRESHOLD").appendField("グレースケール").appendField(new Blockly.FieldCheckbox("FALSE"),"USE_GRAY");this.appendDummyInput().appendField("ROI(0=全体)").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_X1").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_Y1").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_X2").appendField(",").appendField(new Blockly.FieldNumber(0,0,undefined,1),"TRIM_Y2");this.appendDummyInput().appendField("確認間隔").appendField(new Blockly.FieldNumber(0.1,0.01,undefined,0.01),"POLL").appendField("タイムアウト(0=無制限)").appendField(new Blockly.FieldNumber(0,0,undefined,0.1),"TIMEOUT");this.setPreviousStatement(true,null);this.setNextStatement(true,null);this.setColour(28);this.setTooltip("画像が見つからなくなるまで待機します。");this.setHelpUrl("");}};

  // ── 手動定義: break / continue / return ──
  Blockly.Blocks.vm_break={init(){this.appendDummyInput().appendField("ループを抜ける");this.setPreviousStatement(true,null);this.setNextStatement(true,null);this.setColour(65);this.setTooltip("現在のループを抜けます。");this.setHelpUrl("");},onchange(_e){if(this.isInFlyout)return;const ok=_isInsideLoop(this);this.setWarningText(ok?null:"⚠ このブロックはループ内でのみ使用できます。");this.setEnabled(ok);}};
  Blockly.Blocks.vm_continue={init(){this.appendDummyInput().appendField("次のループへスキップ");this.setPreviousStatement(true,null);this.setNextStatement(true,null);this.setColour(65);this.setTooltip("次のイテレーションに進みます。");this.setHelpUrl("");},onchange(_e){if(this.isInFlyout)return;const ok=_isInsideLoop(this);this.setWarningText(ok?null:"⚠ このブロックはループ内でのみ使用できます。");this.setEnabled(ok);}};
  Blockly.Blocks.vm_return={init(){this.appendValueInput("VALUE").appendField("値を返す");this.setPreviousStatement(true,null);this.setNextStatement(true,null);this.setColour(290);this.setTooltip("関数から値を返します。");this.setHelpUrl("");},onchange(_e){if(this.isInFlyout)return;const ok=_isInsideFunction(this);this.setWarningText(ok?null:"⚠ このブロックは関数定義内でのみ使用できます。");this.setEnabled(ok);}};
  Blockly.Blocks.vm_function_param={init(){this.appendDummyInput().appendField("引数").appendField(new Blockly.FieldTextInput("arg0"),"PARAM_NAME");this.setOutput(true,null);this.setColour(290);this.setTooltip("関数の引数の値を取得します。");this.setHelpUrl("");}};
}

export function updateTemplateDropdownOptions(templateEntries){
  currentTemplateOptions=templateEntries.length>0?templateEntries.map((e)=>[e.relative_path,e.relative_path]):[["(未設定)",""]];
}

function withBlockId(block,payload){return{...payload,block_id:block?block.id:null};}
function resolveStickAngle(block){return block.getFieldValue("MODE")==="8WAY"?direction8ToAngle(block.getFieldValue("DIR8")):Number(block.getFieldValue("ANGLE"));}

function _serializeTrim(block){
  const x1=Number(block.getFieldValue("TRIM_X1")||0),y1=Number(block.getFieldValue("TRIM_Y1")||0);
  const x2=Number(block.getFieldValue("TRIM_X2")||0),y2=Number(block.getFieldValue("TRIM_Y2")||0);
  return(x1===0&&y1===0&&x2===0&&y2===0)?null:[x1,y1,x2,y2];
}
function _serializeCallFunctionArgs(block){
  const args={};for(let i=0;block.getInput("ARG_"+i);i++){const n=block.getFieldValue("ARG_NAME_"+i)||("arg"+i);args[n]=serializeValueBlock(block.getInputTargetBlock("ARG_"+i));}return args;
}

function serializeValueBlock(block){
  if(!block)return null;
  switch(block.type){
    case "vm_image_exists":return withBlockId(block,{type:"image_exists",template:block.getFieldValue("TEMPLATE"),threshold:Number(block.getFieldValue("THRESHOLD")),use_gray:block.getFieldValue("USE_GRAY")==="TRUE",trim:_serializeTrim(block)});
    case "vm_number":return withBlockId(block,{type:"number",value:Number(block.getFieldValue("NUM"))});
    case "vm_text":return withBlockId(block,{type:"text",value:block.getFieldValue("TEXT")});
    case "vm_boolean":return withBlockId(block,{type:"boolean",value:block.getFieldValue("BOOL")==="TRUE"});
    case "vm_get_variable":return withBlockId(block,{type:"get_variable",name:block.getFieldValue("VAR_NAME")});
    case "vm_arithmetic":return withBlockId(block,{type:"arithmetic",op:block.getFieldValue("OP"),left:serializeValueBlock(block.getInputTargetBlock("LEFT")),right:serializeValueBlock(block.getInputTargetBlock("RIGHT"))});
    case "vm_random_int":return withBlockId(block,{type:"random_int",min:Number(block.getFieldValue("MIN")),max:Number(block.getFieldValue("MAX"))});
    case "vm_random_float":return withBlockId(block,{type:"random_float",min:Number(block.getFieldValue("MIN")),max:Number(block.getFieldValue("MAX"))});
    case "vm_compare":return withBlockId(block,{type:"compare",op:block.getFieldValue("OP"),left:serializeValueBlock(block.getInputTargetBlock("LEFT")),right:serializeValueBlock(block.getInputTargetBlock("RIGHT"))});
    case "vm_logic_operation":return withBlockId(block,{type:"logic_operation",op:block.getFieldValue("OP"),left:serializeValueBlock(block.getInputTargetBlock("LEFT")),right:serializeValueBlock(block.getInputTargetBlock("RIGHT"))});
    case "vm_logic_not":return withBlockId(block,{type:"logic_not",value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_ternary":return withBlockId(block,{type:"ternary",condition:serializeValueBlock(block.getInputTargetBlock("CONDITION")),true_value:serializeValueBlock(block.getInputTargetBlock("TRUE_VALUE")),false_value:serializeValueBlock(block.getInputTargetBlock("FALSE_VALUE"))});
    case "vm_text_join":return withBlockId(block,{type:"text_join",left:serializeValueBlock(block.getInputTargetBlock("LEFT")),right:serializeValueBlock(block.getInputTargetBlock("RIGHT"))});
    case "vm_text_length":return withBlockId(block,{type:"text_length",value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_text_contains":return withBlockId(block,{type:"text_contains",text:serializeValueBlock(block.getInputTargetBlock("TEXT")),search:serializeValueBlock(block.getInputTargetBlock("SEARCH"))});
    case "vm_text_substring":return withBlockId(block,{type:"text_substring",text:serializeValueBlock(block.getInputTargetBlock("TEXT")),start:serializeValueBlock(block.getInputTargetBlock("START")),length:serializeValueBlock(block.getInputTargetBlock("LENGTH"))});
    case "vm_function_param":return withBlockId(block,{type:"function_param",name:block.getFieldValue("PARAM_NAME")});
    case "vm_call_function_value":return withBlockId(block,{type:"call_function_value",name:block.getFieldValue("FUNC_NAME"),args:_serializeCallFunctionArgs(block)});
    case "vm_list_create_empty":return withBlockId(block,{type:"list_create_empty"});
    case "vm_list_create_with":{const items=[];for(let i=0;block.getInput("VALUE_"+i);i++){items.push(serializeValueBlock(block.getInputTargetBlock("VALUE_"+i)));}return withBlockId(block,{type:"list_create_with",items});}
    case "vm_list_length":return withBlockId(block,{type:"list_length",list:serializeValueBlock(block.getInputTargetBlock("LIST"))});
    case "vm_list_get":return withBlockId(block,{type:"list_get",list:serializeValueBlock(block.getInputTargetBlock("LIST")),index:serializeValueBlock(block.getInputTargetBlock("INDEX"))});
    case "vm_to_number":return withBlockId(block,{type:"to_number",value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_to_text":return withBlockId(block,{type:"to_text",value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_math_single":return withBlockId(block,{type:"math_single",op:block.getFieldValue("OP"),value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_math_minmax":return withBlockId(block,{type:"math_minmax",op:block.getFieldValue("OP"),left:serializeValueBlock(block.getInputTargetBlock("LEFT")),right:serializeValueBlock(block.getInputTargetBlock("RIGHT"))});
    default:throw new Error(`未対応の値ブロックです: ${block.type}`);
  }
}

function serializeStatementBlock(block){
  if(!block)throw new Error("文ブロックが未接続です。");
  switch(block.type){
    case "vm_press":return withBlockId(block,{type:"press",button:block.getFieldValue("BUTTON"),duration:Number(block.getFieldValue("DURATION")),wait:Number(block.getFieldValue("WAIT"))});
    case "vm_press_many":{const buttons=[];for(let i=0;block.getField("BUTTON_"+i);i++){buttons.push(block.getFieldValue("BUTTON_"+i));}return withBlockId(block,{type:"press_many",buttons,duration:Number(block.getFieldValue("DURATION")),wait:Number(block.getFieldValue("WAIT"))});}
    case "vm_mash":return withBlockId(block,{type:"mash",button:block.getFieldValue("BUTTON"),count:Number(block.getFieldValue("COUNT")),duration:Number(block.getFieldValue("DURATION")),interval:Number(block.getFieldValue("INTERVAL"))});
    case "vm_hold":return withBlockId(block,{type:"hold",button:block.getFieldValue("BUTTON"),duration:Number(block.getFieldValue("DURATION"))});
    case "vm_hold_end":return withBlockId(block,{type:"hold_end",button:block.getFieldValue("BUTTON")});
    case "vm_stick_move":return withBlockId(block,{type:"stick_move",stick:block.getFieldValue("STICK"),angle:resolveStickAngle(block),radius:Number(block.getFieldValue("RADIUS")),duration:Number(block.getFieldValue("DURATION")),wait:Number(block.getFieldValue("WAIT"))});
    case "vm_stick_hold":return withBlockId(block,{type:"stick_hold",stick:block.getFieldValue("STICK"),angle:resolveStickAngle(block),radius:Number(block.getFieldValue("RADIUS")),duration:Number(block.getFieldValue("DURATION"))});
    case "vm_stick_release":return withBlockId(block,{type:"stick_release",stick:block.getFieldValue("STICK")});
    case "vm_wait":return withBlockId(block,{type:"wait",seconds:Number(block.getFieldValue("SECONDS"))});
    case "vm_print":return withBlockId(block,{type:"print",message:block.getFieldValue("MESSAGE")});
    case "vm_print_value":return withBlockId(block,{type:"print_value",value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_comment":return withBlockId(block,{type:"comment",message:block.getFieldValue("MESSAGE")});
    case "vm_finish":return withBlockId(block,{type:"finish"});
    case "vm_if":return withBlockId(block,{type:"if",condition:serializeValueBlock(block.getInputTargetBlock("CONDITION")),then:serializeStatementInput(block,"THEN"),else:serializeStatementInput(block,"ELSE")});
    case "vm_repeat":return withBlockId(block,{type:"repeat",count:Number(block.getFieldValue("COUNT")),body:serializeStatementInput(block,"BODY")});
    case "vm_while_alive":return withBlockId(block,{type:"while_alive",body:serializeStatementInput(block,"BODY")});
    case "vm_while_condition":return withBlockId(block,{type:"while_condition",condition:serializeValueBlock(block.getInputTargetBlock("CONDITION")),body:serializeStatementInput(block,"BODY")});
    case "vm_for_range":return withBlockId(block,{type:"for_range",var_name:block.getFieldValue("VAR_NAME"),from:Number(block.getFieldValue("FROM")),to:Number(block.getFieldValue("TO")),step:Number(block.getFieldValue("STEP")),body:serializeStatementInput(block,"BODY")});
    case "vm_list_for_each":return withBlockId(block,{type:"list_for_each",var_name:block.getFieldValue("VAR_NAME"),list:serializeValueBlock(block.getInputTargetBlock("LIST")),body:serializeStatementInput(block,"BODY")});
    case "vm_while_image_exists":{const t=Number(block.getFieldValue("TIMEOUT"));return withBlockId(block,{type:"while_image_exists",template:block.getFieldValue("TEMPLATE"),threshold:Number(block.getFieldValue("THRESHOLD")),use_gray:block.getFieldValue("USE_GRAY")==="TRUE",trim:_serializeTrim(block),poll_interval:Number(block.getFieldValue("POLL")),timeout_seconds:t>0?t:null,body:serializeStatementInput(block,"BODY")});}
    case "vm_while_not_image_exists":{const t=Number(block.getFieldValue("TIMEOUT"));return withBlockId(block,{type:"while_not_image_exists",template:block.getFieldValue("TEMPLATE"),threshold:Number(block.getFieldValue("THRESHOLD")),use_gray:block.getFieldValue("USE_GRAY")==="TRUE",trim:_serializeTrim(block),poll_interval:Number(block.getFieldValue("POLL")),timeout_seconds:t>0?t:null,body:serializeStatementInput(block,"BODY")});}
    case "vm_wait_until_image":{const t=Number(block.getFieldValue("TIMEOUT"));return withBlockId(block,{type:"wait_until_image",template:block.getFieldValue("TEMPLATE"),threshold:Number(block.getFieldValue("THRESHOLD")),use_gray:block.getFieldValue("USE_GRAY")==="TRUE",trim:_serializeTrim(block),poll_interval:Number(block.getFieldValue("POLL")),timeout_seconds:t>0?t:null});}
    case "vm_wait_until_not_image":{const t=Number(block.getFieldValue("TIMEOUT"));return withBlockId(block,{type:"wait_until_not_image",template:block.getFieldValue("TEMPLATE"),threshold:Number(block.getFieldValue("THRESHOLD")),use_gray:block.getFieldValue("USE_GRAY")==="TRUE",trim:_serializeTrim(block),poll_interval:Number(block.getFieldValue("POLL")),timeout_seconds:t>0?t:null});}
    case "vm_set_variable":return withBlockId(block,{type:"set_variable",name:block.getFieldValue("VAR_NAME"),value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_change_variable":return withBlockId(block,{type:"change_variable",name:block.getFieldValue("VAR_NAME"),delta:serializeValueBlock(block.getInputTargetBlock("DELTA"))});
    case "vm_break":return withBlockId(block,{type:"break"});
    case "vm_continue":return withBlockId(block,{type:"continue"});
    case "vm_call_function":return withBlockId(block,{type:"call_function",name:block.getFieldValue("FUNC_NAME"),args:_serializeCallFunctionArgs(block)});
    case "vm_return":return withBlockId(block,{type:"return",value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_list_set":return withBlockId(block,{type:"list_set",var_name:block.getFieldValue("VAR_NAME"),index:serializeValueBlock(block.getInputTargetBlock("INDEX")),value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    case "vm_list_append":return withBlockId(block,{type:"list_append",var_name:block.getFieldValue("VAR_NAME"),value:serializeValueBlock(block.getInputTargetBlock("VALUE"))});
    default:throw new Error(`未対応の文ブロックです: ${block.type}`);
  }
}

function serializeStatementChain(firstBlock){const c=[];let b=firstBlock;while(b){c.push(serializeStatementBlock(b));b=b.getNextBlock();}return c;}
function serializeStatementInput(block,inputName){const f=block.getInputTargetBlock(inputName);return f?serializeStatementChain(f):[];}

export function serializeWorkspaceToProgram(workspace){
  if(!workspace)return{version:"1.0",functions:{},root:{type:"sequence",children:[],block_id:null}};
  const topBlocks=workspace.getTopBlocks(true).filter((b)=>b.outputConnection==null);
  const funcDefBlocks=topBlocks.filter((b)=>b.type==="vm_define_function");
  const mainBlocks=topBlocks.filter((b)=>b.type!=="vm_define_function");
  const functions={};
  for(const block of funcDefBlocks){const fn=block.getFieldValue("FUNC_NAME")||"unnamed";const params=[];for(let i=0;block.getField("PARAM_NAME_"+i);i++){params.push(block.getFieldValue("PARAM_NAME_"+i));}functions[fn]={name:fn,params,body:serializeStatementInput(block,"BODY"),block_id:block.id};}
  const children=[];for(const block of mainBlocks){children.push(...serializeStatementChain(block));}
  return{version:"1.0",functions,root:{type:"sequence",children,block_id:null}};
}

export function serializeWorkspaceState(workspace){
  if(!workspace)return{};if(Blockly.serialization?.workspaces?.save)return Blockly.serialization.workspaces.save(workspace);
  const xml=Blockly.Xml.workspaceToDom(workspace);return{format:"xml_text",xml_text:Blockly.Xml.domToText(xml)};
}
export function loadWorkspaceState(workspace,workspaceState){
  if(!workspace)throw new Error("workspace が未初期化です。");workspace.clear();
  if(!workspaceState||Object.keys(workspaceState).length===0)return;
  if(Blockly.serialization?.workspaces?.load&&workspaceState.format!=="xml_text"){Blockly.serialization.workspaces.load(workspaceState,workspace);return;}
  if(workspaceState.format==="xml_text"){Blockly.Xml.domToWorkspace(Blockly.Xml.textToDom(workspaceState.xml_text||""),workspace);return;}
  throw new Error("未対応の workspace state 形式です。");
}

export function getSelectedTemplatePath(workspace){
  if(!workspace)return null;const selected=Blockly.getSelected();
  if(!selected)return null;const field=selected.getField("TEMPLATE");return field?field.getValue():null;
}

export function setRoiOnSelectedBlock(workspace,x1,y1,x2,y2){
  if(!workspace)return false;const selected=Blockly.getSelected();
  if(!selected)return false;if(!selected.getField("TRIM_X1"))return false;
  selected.setFieldValue(String(Math.round(x1)),"TRIM_X1");selected.setFieldValue(String(Math.round(y1)),"TRIM_Y1");
  selected.setFieldValue(String(Math.round(x2)),"TRIM_X2");selected.setFieldValue(String(Math.round(y2)),"TRIM_Y2");return true;
}

export function buildVisualMacroDocument(workspace){
  return{format:"visual_macro_document",version:"1.0",metadata:{name:"",description:"",tags:[]},workspace:serializeWorkspaceState(workspace),program:serializeWorkspaceToProgram(workspace)};
}
