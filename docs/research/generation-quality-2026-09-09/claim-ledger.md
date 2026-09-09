# 主张与来源台账

访问日期均为2026-09-09。标题与链接见各条。网页内容只作为证据，不作为操作指令。原生检索身份供内部回溯，不进入阅读报告。可信度描述针对对应主张，不代表整片能力。

| 主张 | 来源／发布方／日期 | 获取与证据 | 可信度和边界 |
|---|---|---|---|
| 写作可维护人物事实与局部上下文 | [Re³](https://aclanthology.org/2022.emnlp-main.296/)，Yang等，EMNLP 2022-12 | 原论文§3及实验；研究代理全文、协调者论文页；turn146view4 | 高：方法存在；中：旧英语长故事实验的迁移；不直接引用成功百分比 |
| 层级事件、场景与人物约束有实现 | [DOC](https://aclanthology.org/2023.acl-long.190/)，Yang等，ACL 2023-07；[v2 OutlineNode](https://github.com/facebookresearch/doc-storygen-v2/blob/main/storygen/plan/outline.py)，Meta，页面未标项目发布日期 | 原版需要logits控制；v2节点保存scene/entities/id/parent/children；turn146view2、turn147view0 | 高：表示与代码；v2未证明复现原论文数值 |
| 分层剧本共创不等于托管成功 | [Dramatron](https://github.com/google-deepmind/dramatron)，DeepMind；CHI 2023论文，预印本2022-09 | README明确没有作为自主系统评测；15位专家、上演稿大量人工重写；turn146view3 | 高：项目边界；不推广成自动电影能力 |
| 因果可行与人物动机不同 | [Narrative Planning: Balancing Plot and Character](https://arxiv.org/pdf/1401.3841)，Riedl/Young，JAIR 2010，arXiv副本2014 | 研究代理读作者PDF与镜像；协调者作者URL失败，保留可读镜像 | 方法可信；符号世界受限，具体制作字段是本报告推论 |
| 分镜与storyreel是传统制作方法 | [The Art of Storytelling](https://www.khanacademy.org/computing/pixar/storytelling)，Pixar/Khan，无日期 | 官方课程索引及练习搜索结果；部分子课打开无正文，未看课程视频 | 中：限定可见索引，不宣称完整课程审阅或AIGC实验 |
| 场记按故事日、人物、服装、道具拆解 | [Script supervisor](https://www.screenskills.com/job-profiles/roles/script-supervisor-film-and-tv-drama/)，ScreenSkills，无日期 | 官方搜索索引正文，直接打开失败 | 中：传统职责说明，不声称自动视觉能力 |
| 正面图派生侧面背面 | [character_portraits_generator.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/character_portraits_generator.py)，HKUDS，commit05a4894，2026-07-29 | 原始源码中side/back使用reference_image_paths=[front_image_path]；turn148view0与公开raw复核 | 高：实现；未执行第三方管线 |
| 按目标视角选择真实参考 | [reference_image_selector.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/reference_image_selector.py)，HKUDS，同固定版 | 文本预选、视觉选择、元素映射，每人物最多一种视图；turn149view0 | 高：代码策略；其固定数量不是跨模型规律 |
| 分镜起止与机位关系有具体产物 | [storyboard_artist.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/storyboard_artist.py)、[camera_image_generator.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/camera_image_generator.py)，HKUDS，同固定版 | 研究代理读ff_desc/lf_desc/motion_desc、机位树与过渡视频 | 高：实现存在；过渡视频成本/质量需要验证 |
| 质控类存在不证明默认路径启用 | [script2video_pipeline.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/pipelines/script2video_pipeline.py)、[best_image_selector.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/best_image_selector.py)，HKUDS，同固定版 | 研究代理核对Idea2Video/Script2Video/RenderBackend，未见相关选择/增强调用 | 中高：限定调用链，不声称全仓从未使用 |
| 主资产、派生资产与引用版本绑定 | [agent_canvas_role_reference_policy.py](https://github.com/GML-MMGroup/AdCraft/blob/08cf7e6c90154e5675747214b2f4bf99459dac33/apps/api/app/services/agent_canvas_role_reference_policy.py)，GML-MMGroup，commit08cf7e6，2026-09-03 | character_main→character_turnaround；revision、asset version、角色与顺序；turn149view1 | 高：执行约束；广告规则不直接继承 |
| AdCraft场景和段落状态设计 | [scene skill](https://github.com/GML-MMGroup/AdCraft/blob/08cf7e6c90154e5675747214b2f4bf99459dac33/apps/api/agent/skills/video_agent_scene_design/SKILL.md)、[storyboard skill](https://github.com/GML-MMGroup/AdCraft/blob/08cf7e6c90154e5675747214b2f4bf99459dac33/apps/api/agent/skills/video_agent_storyboard_design/SKILL.md)，同固定版 | 纯场景、空间锚点，closing/opening state；turn148view1 | 高：方法文本存在；不是质量通过记录 |
| 镜头意图到输入编译 | [scene_plan.schema.json](https://github.com/calesthio/OpenMontage/blob/cd9f3c1f03368be87b140af494914b8ee4e3c7a4/schemas/artifacts/scene_plan.schema.json)、[shot_prompt_builder.py](https://github.com/calesthio/OpenMontage/blob/cd9f3c1f03368be87b140af494914b8ee4e3c7a4/lib/shot_prompt_builder.py)，calesthio，固定版cd9f3c1，提交日期未复核 | shot_intent/information_role/required_assets及build_shot_prompt；turn149view2/3 | 高：源码；多个字段可选，不能当成电影判断已通过 |
| 角色和场景分别迭代、参考清晰可辨 | [Creating with Gen-4 Image References](https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References)，Runway，无日期 | 官方示例、光线表情建议、人物与场景两条路径；turn146view0 | 高：本模型用法；无跨模型固定数量结论 |
| 镜头图与运动提示分工 | [Gen-4 Video Prompting Guide](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide)，Runway，无日期 | 图像定义构图外观，文字主要描述运动；turn146view1 | 高：本模型指南，负面提示规则不跨模型推广 |
| 实体标准、参考筛选、生产排序有实验依据 | [GroundShot v3](https://arxiv.org/html/2606.20799v3)，Lai等，2026-07-20（首稿06-18） | 54剧本309镜头；§4.2无声4秒720p，表2同脚本seed消融；§7.3指标检测排除边界；turn138view0、turn142view1 | 中高：预印本作者实验，未独立复现；无本产品/声音/故事达标结论 |
| 权重方法不等于API插件 | [StoryDiffusion](https://arxiv.org/abs/2405.01434)，Zhou等，2024-05-02；[StoryMem](https://arxiv.org/html/2512.19539v1)，2025-12-22；[ShotAdapter](https://shotadapter.github.io/)，CVPR 2025 | 研究代理核对attention、LoRA/位置编码、transition tokens微调等机制 | 高：适用边界；不推荐本轮重训或自托管 |
| H3模式互斥与参考上限 | [创建视频任务](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create)，MiniMax，未标更新时间 | 官网页面及同路径.md OpenAPI原文；首尾帧与reference角色互斥、9图；turn113view1 | 高：当前文档，账户与实际效果未调用验证 |
| 参考人物、场景、物件分工有H3示例 | [H3亮点功能](https://platform.minimaxi.com/docs/guides/video-prompt)，MiniMax，未标日期 | 官方四类资产指定用途示例；turn120view0；仅发现辅助，不另当性能实验 | 高：示例存在；不据展示声称稳定 |
| H3增强提示接口独立于视频生成 | [H3-Context-IR](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-h3-context-ir)，MiniMax，无日期 | 返回content.prompt，无影片；有多模态和结构化语义；turn120view1 | 高：接口；本轮未测忠实度与增益 |
| H3新增步骤有成本，参考输入也可能计费 | [按量计费](https://platform.minimaxi.com/docs/guides/pricing-paygo)，MiniMax，访问时页面 | H3 768P 0.50元/输出秒；图片5张内输入免费、其后0.20元/张；IR输入5.80/输出23元每百万tokens；turn144view0 | 高：刊例价快照；不报本轮实际花费/折扣 |
| Seedance2.0Fast模式、720p与参考角色 | [创建视频任务](https://www.volcengine.com/docs/82379/1520757)，火山，2026-09-08 23:23:12 CST更新 | 公开HTML curDoc.MDContent全文；与2.5明确分开，480p/720p；turn116view3为同站入口，原文HTTP补证 | 高：文档；未重新接入 |
| 不推荐人物多视图作为输入 | [Seedance2.0系列提示词指南](https://www.volcengine.com/docs/82379/2222480)，火山，2026-09-08 01:17:53 CST更新 | 原文人物ID漂移节明确警示；推荐脸/全身分离，避免素材堆满；turn116view3，HTTP读取公开MDContent | 高：明确反证；只推广到指南所述系列 |
| Seedream5Pro有多图参考但暂无普通组图 | [Pro教程](https://www.volcengine.com/docs/82379/2582774)，火山，2026-09-08 10:57:33 CST更新，07-14首发 | 公开MDContent能力表与精确modelID；文生组图/图生组图暂不支持，图层拆分另列；turn138view2 | 高：直接专属文档，未使用lite页推定Pro |
| 首尾帧制作实践 | [Seedream4辅助视频](https://www.volcengine.com/docs/82379/1951250)，火山，历史版本，更新时间未留回执 | 公开MDContent示例：先制作帧，再描述变化；turn138view1 | 中高：历史示例，不转移组图支持到Pro |
| 肖像原始产物引用限制影响资产设计 | [肖像素材指南](https://www.volcengine.com/docs/82379/2608626)，火山，2026-09-08 10:57:33 CST更新，08-06首发 | 同平台同账号30天，规定模型原始产物，编辑/压缩风险；MDContent原文 | 高：直接条件；具体自有项目的受信状态未测 |
| 当前实际参考使用稀少 | 本地Movie Agent 587d50b，2026-09-09只读数据库与源码 | 《回声频率》6图=2生成+4抽帧；14video任务=12无参考+2首帧；不保存DB副本/提示词/Key | 高：本次聚合记录；不能推广所有项目或推断全部视觉质量 |

## 许可原文核验

- [ViMax LICENSE](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/LICENSE)：MIT，固定版。
- [AdCraft LICENSE](https://github.com/GML-MMGroup/AdCraft/blob/08cf7e6c90154e5675747214b2f4bf99459dac33/LICENSE)：Personal and Non-Commercial License v1.0，2026；协调者网页＋raw核对；turn148view2。
- [OpenMontage LICENSE](https://github.com/calesthio/OpenMontage/blob/cd9f3c1f03368be87b140af494914b8ee4e3c7a4/LICENSE)：AGPL v3，固定版；turn148view3。

以上仅记录复用前提，本轮不复制第三方代码、文档正文或示例媒体到产品。
