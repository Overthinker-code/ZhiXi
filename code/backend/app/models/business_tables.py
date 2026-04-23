"""加载根目录 `app/models.py` 中的业务表模型（教育/视频等），只注册一次 MetaData。

`app/core/db.py` 不再对该文件做 importlib，避免与 `app.models.user.User` 重复注册 `user` 表。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_domain_models():
    key = "app._domain_models_from_models_py"
    if key in sys.modules:
        return sys.modules[key]
    path = Path(__file__).resolve().parent.parent / "models.py"
    spec = importlib.util.spec_from_file_location(key, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_domain_models()

Course = _mod.Course
UD = _mod.UD
Teacher = _mod.Teacher
TC = _mod.TC
Student = _mod.Student
StudentTC = _mod.StudentTC
Video = _mod.Video
CoursePlan = _mod.CoursePlan
Log = _mod.Log
HelpDocument = _mod.HelpDocument
Assignment = _mod.Assignment
Submission = _mod.Submission
LearningActivity = _mod.LearningActivity
ChatLog = _mod.ChatLog
Alert = _mod.Alert
Resource = _mod.Resource
ResourceCreate = _mod.ResourceCreate
ResourceUpdate = _mod.ResourceUpdate
ResourcePublic = _mod.ResourcePublic
ResourcesPublic = _mod.ResourcesPublic
