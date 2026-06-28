# ci-templates

Reusable GitLab CI templates for the ADSUM platform, plus the Constitution
audit engine (PLAYBOOK section 1, I1 to I11).

## Templates

- `templates/base.yml` - Constitution audit (em-dash, mock, file size). Included by all.
- `templates/node.yml` - Node / TypeScript lint, test, build.
- `templates/python.yml` - Python lint (ruff) and tests (pytest).
- `templates/terraform.yml` - Terraform fmt, init, validate.

## Usage

In a repository `.gitlab-ci.yml`:

```yaml
include:
  - project: 'sr-media-ai/adsum/deployment/ci-templates'
    ref: main
    file: '/templates/node.yml'
```
