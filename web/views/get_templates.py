from starlette.responses import JSONResponse

def create_get_templates(template_manager):
    async def get_templates(request):
        return JSONResponse({"templates": template_manager.list_templates()})
    return get_templates
