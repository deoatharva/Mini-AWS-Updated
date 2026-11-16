# Product Requirements Document

## Goal
Build a functional local cloud lab for practicals 11–15 using React and FastAPI.

## Core features
- Local account registration and login
- Create/start/stop/delete compute instances
- Deploy a controlled sample web application and show its local URL
- Create storage buckets and upload/download/delete files
- Create isolated local databases and execute SQL
- Dashboard, activity history, validation, and useful error messages

## Non-goals
- Creating or representing a real AWS account
- Public cloud hosting or billing
- Production multi-tenant hosting

## Acceptance criteria
Features must operate on real local resources, return accurate status, handle errors, and have automated tests. Do not use fake success states.
