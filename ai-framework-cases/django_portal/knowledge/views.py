import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from ai_client import ModelServiceError, answer_sync
from .models import Document


@staff_member_required
def demo(request):
    return render(request, "knowledge/demo.html")


@staff_member_required
@require_POST
def ask(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "请输入 JSON"}, status=400)
    question = data.get("question") if isinstance(data, dict) else None
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        return JsonResponse({"error": "问题须为 1–500 字符的非空文字"}, status=400)
    docs = list(Document.objects.filter(active=True).order_by("id")[:5])
    if not docs:
        return JsonResponse({"error": "没有有效资料，请先在 Admin 添加文档"}, status=409)
    sources = [{"id": f"S{i+1}", "title": doc.title, "text": doc.text[:1800]}
               for i, doc in enumerate(docs)]
    context = "\n\n".join(f"[{s['id']}] {s['title']}\n{s['text']}" for s in sources)
    try:
        answer = answer_sync(question.strip(), context=context)
    except ModelServiceError:
        return JsonResponse({"error": "模型服务暂不可用，请检查 Ollama"}, status=502)
    return JsonResponse({"answer": answer, "sources": sources,
                         "note": "少量有效资料作为上下文；无向量检索，答案需要人工核对"})
