/**
 * 义务↔制度条款 多对多关系表（层 3）
 *
 * 每条记录描述一个"法规义务条款"与"内部制度条款"之间的映射关系。
 * 同一法规义务可对应多条制度条款（一对多），同一制度条款也可被多个义务引用（多对一）。
 *
 * 字段说明：
 *   id              - 映射记录唯一标识，格式 MAP-XXX
 *   lawId           - 所属法规 ID，对应 laws[].id（如 LAW-CSL / LAW-DS / LAW-PIPL）
 *   obligationId    - 法规义务条款 ID，对应 laws[].obligations[].id
 *                     （如 OBG-001 为网络安全法第一条）
 *   policyClauseId  - 内部制度条款 ID，对应 policies[].clauses[].id
 *                     null = 该义务尚无制度条款覆盖（制度缺口）
 *   mappingStatus   - 覆盖状态，取值：
 *                       "已覆盖"   制度条款已明确落地该义务
 *                       "部分覆盖" 制度条款仅覆盖义务的部分要求
 *                       "制度缺口" 有义务但无对应制度条款
 *                       "不适用"   该义务不要求企业直接履行（国家层面/倡导性/监管部门职责等）
 *   managementAction - 针对该义务，内部已采取或计划采取的管理/技术措施描述
 *                      "不适用" 时留空
 *   remark          - 备注说明，解释映射判断依据、偏差原因或补充说明
 */

export const obligationMappings = [
  {
    id: "MAP-001",
    lawId: "LAW-CSL",
    obligationId: "OBG-001",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "立法宗旨条款，不要求企业落实具体措施"
  },
  {
    id: "MAP-002",
    lawId: "LAW-CSL",
    obligationId: "OBG-002",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "适用范围界定，不产生直接义务"
  },
  {
    id: "MAP-003",
    lawId: "LAW-CSL",
    obligationId: "OBG-003",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "国家战略方针，非企业义务"
  },
  {
    id: "MAP-004",
    lawId: "LAW-CSL",
    obligationId: "OBG-004",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "同上"
  },
  {
    id: "MAP-005",
    lawId: "LAW-CSL",
    obligationId: "OBG-005",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "国家层面行动，企业不承担此义务"
  },
  {
    id: "MAP-006",
    lawId: "LAW-CSL",
    obligationId: "OBG-006",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "倡导性内容，不要求具体措施"
  },
  {
    id: "MAP-007",
    lawId: "LAW-CSL",
    obligationId: "OBG-007",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "国家层面"
  },
  {
    id: "MAP-008",
    lawId: "LAW-CSL",
    obligationId: "OBG-008",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "部门职责分工，企业需配合但无对应动作"
  },
  {
    id: "MAP-009",
    lawId: "LAW-CSL",
    obligationId: "OBG-009",
    policyClauseId: "PC-001",
    mappingStatus: "已覆盖",
    managementAction: "为加强网络通信安全技术管控，依据法规制定本规范",
    remark: "总则明确了遵守法规、履行保护义务的意图"
  },
  {
    id: "MAP-010",
    lawId: "LAW-CSL",
    obligationId: "OBG-010",
    policyClauseId: "PC-002",
    mappingStatus: "已覆盖",
    managementAction: "规范覆盖网络架构、通信安全、边界防护、入侵防范等技术措施",
    remark: "通过多个章节的技术要求实现"
  },
  {
    id: "MAP-011",
    lawId: "LAW-CSL",
    obligationId: "OBG-011",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "行业组织行为，企业不承担"
  },
  {
    id: "MAP-012",
    lawId: "LAW-CSL",
    obligationId: "OBG-012",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "第一款不适用，第二款是对个人的要求，企业可通过用户协议约束，但无直接对应的技术规范要求"
  },
  {
    id: "MAP-013",
    lawId: "LAW-CSL",
    obligationId: "OBG-013",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "银行主要面向企业及成年人，未成年人保护非核心场景，暂不适用"
  },
  {
    id: "MAP-014",
    lawId: "LAW-CSL",
    obligationId: "OBG-014",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "举报受理为监管部门职责，企业无直接对应，但第四十九条要求建立投诉举报制度"
  },
  {
    id: "MAP-015",
    lawId: "LAW-CSL",
    obligationId: "OBG-015",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "国家层面"
  },
  {
    id: "MAP-016",
    lawId: "LAW-CSL",
    obligationId: "OBG-016",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "国家层面"
  },
  {
    id: "MAP-017",
    lawId: "LAW-CSL",
    obligationId: "OBG-017",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "国家层面"
  },
  {
    id: "MAP-018",
    lawId: "LAW-CSL",
    obligationId: "OBG-018",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "鼓励性条款"
  },
  {
    id: "MAP-019",
    lawId: "LAW-CSL",
    obligationId: "OBG-019",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "非企业强制义务"
  },
  {
    id: "MAP-020",
    lawId: "LAW-CSL",
    obligationId: "OBG-020",
    policyClauseId: null,
    mappingStatus: "不适用",
    managementAction: "",
    remark: "鼓励性"
  },
  {
    id: "MAP-021",
    lawId: "LAW-CSL",
    obligationId: "OBG-022",
    policyClauseId: "PC-001",
    mappingStatus: "已覆盖",
    managementAction: "制定本规范作为管理制度的一部分",
    remark: "规范本身即为制度"
  },
  {
    id: "MAP-022",
    lawId: "LAW-CSL",
    obligationId: "OBG-023",
    policyClauseId: "PC-003",
    mappingStatus: "已覆盖",
    managementAction: "明确网络安全管理处、网络运营处、科技资源管理处、开发测试中心的职责分工",
    remark: "职责条款明确了责任主体"
  },
  {
    id: "MAP-023",
    lawId: "LAW-CSL",
    obligationId: "OBG-024",
    policyClauseId: "PC-004",
    mappingStatus: "已覆盖",
    managementAction: "部署IDS/NDR/蜜罐、恶意代码检测等",
    remark: "覆盖已知攻击、未知威胁、主动诱捕"
  },
  {
    id: "MAP-024",
    lawId: "LAW-CSL",
    obligationId: "OBG-025",
    policyClauseId: "PC-005",
    mappingStatus: "已覆盖",
    managementAction: "启用日志记录功能",
    remark: "明确了日志记录要求"
  },
  {
    id: "MAP-025",
    lawId: "LAW-CSL",
    obligationId: "OBG-026",
    policyClauseId: "PC-006",
    mappingStatus: "已覆盖",
    managementAction: "日志记录保存时间不少于6个月",
    remark: "直接对应，数字完全一致"
  }

]
