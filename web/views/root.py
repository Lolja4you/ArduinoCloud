from starlette.responses import JSONResponse
def create_root():
    async def root(request):
        return JSONResponse({"message": "Sensor Data API is running"})
    return root