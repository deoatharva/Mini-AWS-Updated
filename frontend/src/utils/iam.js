export const ACTION_CATEGORY_LABELS = {
  dashboard: 'Console dashboard',
  compute: 'Compute',
  applications: 'Application deployment',
  storage: 'Object storage',
  database: 'Databases',
  iam: 'Identity and access management',
};

export const EVENT_TYPES = [
  'account.registered',
  'auth.signin_succeeded',
  'auth.signin_failed',
  'auth.password_changed',
  'auth.password_reset',
  'iam.user.created',
  'iam.user.updated',
  'iam.user.activated',
  'iam.user.deactivated',
  'iam.user.deleted',
  'iam.group.created',
  'iam.group.updated',
  'iam.group.deleted',
  'iam.group.member_added',
  'iam.group.member_removed',
  'iam.policy.created',
  'iam.policy.updated',
  'iam.policy.deleted',
  'iam.policy.attached',
  'iam.policy.detached',
];

const EVENT_LABELS = {
  'account.registered': 'Account registered',
  'auth.signin_succeeded': 'Sign-in succeeded',
  'auth.signin_failed': 'Sign-in failed',
  'auth.password_changed': 'Password changed',
  'auth.password_reset': 'Password reset by administrator',
  'iam.user.created': 'IAM user created',
  'iam.user.updated': 'IAM user updated',
  'iam.user.activated': 'IAM user activated',
  'iam.user.deactivated': 'IAM user deactivated',
  'iam.user.deleted': 'IAM user deleted',
  'iam.group.created': 'IAM group created',
  'iam.group.updated': 'IAM group updated',
  'iam.group.deleted': 'IAM group deleted',
  'iam.group.member_added': 'User added to group',
  'iam.group.member_removed': 'User removed from group',
  'iam.policy.created': 'Policy created',
  'iam.policy.updated': 'Policy updated',
  'iam.policy.deleted': 'Policy deleted',
  'iam.policy.attached': 'Policy attached to group',
  'iam.policy.detached': 'Policy detached from group',
};

export function eventLabel(eventType) {
  return EVENT_LABELS[eventType] || eventType;
}

export function categoryLabel(category) {
  return ACTION_CATEGORY_LABELS[category] || category;
}

export function groupActions(actions) {
  const groups = new Map();
  for (const item of actions) {
    const action = typeof item === 'string' ? item : item.action;
    const category = action.split(':', 1)[0];
    if (!groups.has(category)) {
      groups.set(category, []);
    }
    groups.get(category).push(item);
  }
  return [...groups.entries()].sort(([left], [right]) =>
    left.localeCompare(right),
  );
}
