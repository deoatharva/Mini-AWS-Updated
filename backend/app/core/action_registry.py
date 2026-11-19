"""One source of truth for protected actions and built-in policy documents.

This is an intentionally small allow-list model for a local teaching lab. It
does not implement AWS wildcard, Deny, condition, or boundary semantics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDefinition:
    name: str
    description: str
    version: int
    actions: frozenset[str]


ACTION_DESCRIPTIONS: dict[str, str] = {
    "dashboard:Read": "View the console dashboard and account resource totals.",
    "compute:ListInstances": "List compute instances.",
    "compute:GetInstance": "View compute instance details.",
    "compute:CreateInstance": "Create compute instances.",
    "compute:StartInstance": "Start compute instances.",
    "compute:StopInstance": "Stop compute instances.",
    "compute:DeleteInstance": "Delete compute instances.",
    "compute:ReadLogs": "Read compute instance logs.",
    "applications:ListDeployments": "List application deployments.",
    "applications:GetDeployment": "View application deployment details.",
    "applications:CreateDeployment": "Create application deployments.",
    "applications:StartDeployment": "Start application deployments.",
    "applications:StopDeployment": "Stop application deployments.",
    "applications:DeleteDeployment": "Delete application deployments.",
    "applications:ReadLogs": "Read application deployment logs.",
    "storage:ListBuckets": "List storage buckets.",
    "storage:CreateBucket": "Create storage buckets.",
    "storage:DeleteBucket": "Delete storage buckets.",
    "storage:ListObjects": "List files in storage buckets.",
    "storage:DownloadObject": "Download stored objects.",
    "storage:UploadObject": "Upload or replace stored objects.",
    "storage:DeleteObject": "Delete stored objects.",
    "database:ListDatabases": "List local database resources.",
    "database:CreateDatabase": "Create local database resources.",
    "database:DeleteDatabase": "Delete local database resources.",
    "database:ListTables": "Inspect database tables and columns.",
    "database:ExecuteSql": "Execute SQL against a local database.",
    "iam:ReadOverview": "View the IAM overview.",
    "iam:ListUsers": "List IAM users.",
    "iam:GetUser": "View IAM user details and effective permissions.",
    "iam:CreateUser": "Create IAM users.",
    "iam:UpdateUser": "Edit, activate, or deactivate IAM users.",
    "iam:DeleteUser": "Delete IAM users.",
    "iam:ResetUserPassword": "Reset an IAM user's password.",
    "iam:ListGroups": "List IAM groups.",
    "iam:GetGroup": "View IAM group details.",
    "iam:CreateGroup": "Create IAM groups.",
    "iam:UpdateGroup": "Edit IAM groups.",
    "iam:DeleteGroup": "Delete IAM groups.",
    "iam:AddUserToGroup": "Add IAM users to groups.",
    "iam:RemoveUserFromGroup": "Remove IAM users from groups.",
    "iam:AttachGroupPolicy": "Attach policies to groups.",
    "iam:DetachGroupPolicy": "Detach policies from groups.",
    "iam:ListPolicies": "List built-in and custom policies.",
    "iam:GetPolicy": "View policy documents.",
    "iam:CreatePolicy": "Create custom policies.",
    "iam:UpdatePolicy": "Edit custom policies.",
    "iam:DeletePolicy": "Delete custom policies.",
    "iam:ListAuditLogs": "View identity-management audit logs.",
}

VALID_ACTIONS = frozenset(ACTION_DESCRIPTIONS)

DASHBOARD_READ = {"dashboard:Read"}
COMPUTE_ACTIONS = {
    "compute:ListInstances",
    "compute:GetInstance",
    "compute:CreateInstance",
    "compute:StartInstance",
    "compute:StopInstance",
    "compute:DeleteInstance",
    "compute:ReadLogs",
    "applications:ListDeployments",
    "applications:GetDeployment",
    "applications:CreateDeployment",
    "applications:StartDeployment",
    "applications:StopDeployment",
    "applications:DeleteDeployment",
    "applications:ReadLogs",
}
STORAGE_ACTIONS = {
    "storage:ListBuckets",
    "storage:CreateBucket",
    "storage:DeleteBucket",
    "storage:ListObjects",
    "storage:DownloadObject",
    "storage:UploadObject",
    "storage:DeleteObject",
}
DATABASE_ACTIONS = {
    "database:ListDatabases",
    "database:CreateDatabase",
    "database:DeleteDatabase",
    "database:ListTables",
    "database:ExecuteSql",
}
IAM_READ_ACTIONS = {
    "iam:ReadOverview",
    "iam:ListUsers",
    "iam:GetUser",
    "iam:ListGroups",
    "iam:GetGroup",
    "iam:ListPolicies",
    "iam:GetPolicy",
}
IAM_MANAGEMENT_ACTIONS = IAM_READ_ACTIONS | {
    "iam:CreateUser",
    "iam:UpdateUser",
    "iam:DeleteUser",
    "iam:ResetUserPassword",
    "iam:CreateGroup",
    "iam:UpdateGroup",
    "iam:DeleteGroup",
    "iam:AddUserToGroup",
    "iam:RemoveUserFromGroup",
    "iam:AttachGroupPolicy",
    "iam:DetachGroupPolicy",
}
READ_ONLY_ACTIONS = DASHBOARD_READ | {
    "compute:ListInstances",
    "compute:GetInstance",
    "compute:ReadLogs",
    "applications:ListDeployments",
    "applications:GetDeployment",
    "applications:ReadLogs",
    "storage:ListBuckets",
    "storage:ListObjects",
    "storage:DownloadObject",
    "database:ListDatabases",
    "database:ListTables",
}

POLICY_DEFINITIONS: dict[str, PolicyDefinition] = {
    "AdministratorAccess": PolicyDefinition(
        name="AdministratorAccess",
        description=(
            "All supported Mini AWS actions, including IAM administration and "
            "audit logs. Only grant this to users who need full account access."
        ),
        version=1,
        actions=VALID_ACTIONS,
    ),
    "ReadOnlyAccess": PolicyDefinition(
        name="ReadOnlyAccess",
        description=(
            "View and list compute, application, storage, and database resources. "
            "Does not allow creating, changing, starting, stopping, or deleting."
        ),
        version=1,
        actions=frozenset(READ_ONLY_ACTIONS),
    ),
    "ComputeAccess": PolicyDefinition(
        name="ComputeAccess",
        description=(
            "Manage compute instances and application deployments, including "
            "start, stop, logs, and deletion."
        ),
        version=1,
        actions=frozenset(DASHBOARD_READ | COMPUTE_ACTIONS),
    ),
    "StorageAccess": PolicyDefinition(
        name="StorageAccess",
        description="Create buckets and upload, download, or delete stored objects.",
        version=1,
        actions=frozenset(DASHBOARD_READ | STORAGE_ACTIONS),
    ),
    "DatabaseAccess": PolicyDefinition(
        name="DatabaseAccess",
        description="Create local databases, inspect schemas, and execute SQL.",
        version=1,
        actions=frozenset(DASHBOARD_READ | DATABASE_ACTIONS),
    ),
    "IAMReadOnlyAccess": PolicyDefinition(
        name="IAMReadOnlyAccess",
        description="View IAM users, groups, and policies, but make no changes.",
        version=1,
        actions=frozenset(DASHBOARD_READ | IAM_READ_ACTIONS),
    ),
    "IAMManagementAccess": PolicyDefinition(
        name="IAMManagementAccess",
        description=(
            "Manage IAM users, groups, memberships, and group policy attachments. "
            "Cannot change the owner identity or grant itself new permissions."
        ),
        version=1,
        actions=frozenset(DASHBOARD_READ | IAM_MANAGEMENT_ACTIONS),
    ),
}


def policy_document(actions: set[str] | frozenset[str]) -> dict:
    """Return the persisted structured allow-list document for an action set."""
    return {
        "Version": "2026-11-19",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": sorted(_validated_actions(actions)),
            }
        ],
    }


def document_actions(document: object) -> set[str]:
    """Read allowed actions from a stored document, ignoring unknown entries."""
    if not isinstance(document, dict):
        return set()
    statements = document.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list):
        return set()
    actions: set[str] = set()
    for statement in statements:
        if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
            continue
        raw_actions = statement.get("Action", [])
        if isinstance(raw_actions, str):
            raw_actions = [raw_actions]
        if not isinstance(raw_actions, list):
            continue
        for action in raw_actions:
            if isinstance(action, str) and action in VALID_ACTIONS:
                actions.add(action)
    return actions


def _validated_actions(actions: set[str] | frozenset[str]) -> set[str]:
    invalid = set(actions) - VALID_ACTIONS
    if invalid:
        raise ValueError(f"Unknown actions: {', '.join(sorted(invalid))}")
    return set(actions)


def action_catalog() -> list[dict[str, str]]:
    return [
        {
            "action": action,
            "description": ACTION_DESCRIPTIONS[action],
            "category": action.split(":", 1)[0],
        }
        for action in sorted(ACTION_DESCRIPTIONS)
    ]
