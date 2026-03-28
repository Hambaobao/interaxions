"""
Sample: workflow.yaml 定义 → 渲染 Hera Workflow YAML

展示从声明式 workflow 定义到最终可提交 Argo Workflow 的完整流程：

  workflow.yaml  ──►  AutoWorkflow.from_repo()  ──►  DeclarativeWorkflow
                                                          │
                                Job (params)  ────────────►  create_workflow(job)
                                                          │
                                                          ▼
                                                    Hera Workflow  ──►  .to_yaml()

运行方式（从项目根目录）：
    uv run python demos/sample_workflow.py
"""

from pathlib import Path

from interaxions import AutoWorkflow, Job
from interaxions.schemas import (
    RuntimeConfig,
    WorkflowConfig,
    TTLConfig,
    RetryConfig,
    BackoffConfig,
)

# ---------------------------------------------------------------------------
# 1. 加载声明式 workflow（从本地 demo 仓库）
# ---------------------------------------------------------------------------

DEMOS_DIR = Path(__file__).parent
WORKFLOW_REPO = DEMOS_DIR / "repos" / "SWE-rollout-verify-workflow"

workflow = AutoWorkflow.from_repo(WORKFLOW_REPO)

print(f"Loaded workflow  : {type(workflow).__name__}")
print(f"Workflow type    : {workflow._definition.type}")
print(f"Workflow name    : {workflow._definition.name}")
print(f"Inputs           : {[i.name for i in workflow._definition.inputs]}")
print(f"Steps            : {[s.id for s in workflow._definition.steps]}")
print()

# ---------------------------------------------------------------------------
# 2. 构造 Job，将 workflow 参数传入
#
#    task 类型的 inputs（fetch_task / agent_task / verify_task）接受本地路径，
#    WorkflowTranslator 会直接把它传给 AutoTask.from_repo() 去加载对应任务。
# ---------------------------------------------------------------------------

job = Job(
    name="swe-bench-sample",
    labels={"team": "research", "env": "prod"},
    annotations={"description": "SWE-bench sample run"},
    workflow=WorkflowConfig(
        repo_name_or_path=str(WORKFLOW_REPO),
        params={
            # 必填：SWE-bench 实例 ID
            "instance_id": "django__django-12345",

            # task 类型的 inputs：指向本地 demo 仓库（生产环境填 hub 路径如 ix-hub/SWE-bench-fetch）
            "fetch_task": str(DEMOS_DIR / "repos" / "SWE-bench-fetch"),
            "agent_task": str(DEMOS_DIR / "repos" / "SWE-agent"),
            "verify_task": str(DEMOS_DIR / "repos" / "SWE-bench-verify"),

            # 模型配置（object 类型，WorkflowTranslator 会 JSON 序列化后传给任务）
            "model": {
                "type": "litellm",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "base_url": "https://api.anthropic.com",
                "api_key": "sk-ant-...",
            },

            # 可选参数（不填则使用 workflow.yaml 中的 default）
            "max_iterations": 50,
            "predictions_path": "gold",
            "job_id": "job-demo-001",
        },
    ),
    runtime=RuntimeConfig(
        namespace="argo",
        service_account="argo-workflow",
        ttl=TTLConfig(seconds_after_success=60, seconds_after_failure=1800),
        retry=RetryConfig(limit=3, backoff=BackoffConfig(duration="1m", factor=2)),
        pod_gc_strategy="OnWorkflowSuccess",
        dns_policy="ClusterFirst",
    ),
)

# ---------------------------------------------------------------------------
# 3. 翻译为 Hera Workflow
#
#    WorkflowTranslator 会：
#      - 解析 ${{ inputs.xxx }} 表达式
#      - 对每个 step 调用 AutoTask.from_repo(uses) 加载任务
#      - 调用 task.create_task(**kwargs) 构造 Hera Task
#      - 将 ${{ steps.ID.outputs.NAME }} 转换为 Argo artifact/parameter 引用
#      - 组装 DAG 并返回 Hera Workflow
# ---------------------------------------------------------------------------

print("Translating workflow...")
hera_workflow = workflow.create_workflow(job)
print("Translation complete.")
print()

# ---------------------------------------------------------------------------
# 4. 输出渲染后的 Argo Workflow YAML
# ---------------------------------------------------------------------------

print("=" * 60)
print("Rendered Argo Workflow YAML")
print("=" * 60)
print(hera_workflow.to_yaml())
