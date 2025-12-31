from database import get_db

async def test():
    async for db in get_db():
        print("Sessão criada com sucesso!")

import asyncio
asyncio.run(test())