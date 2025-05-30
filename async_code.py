import logging
import asyncio
import time
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
MONGO_URI = 'mongodb://root:root@localhost:27019'
DB_NAME = 'products'
COLLECTION_NAME = 'gmc_products'

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
target_collection = db["new_collection"]

async def fetch_products(batch_size, last_id=None):
    query = {'_id': {'$gt': last_id}} if last_id else {}
    cursor = collection.find(query).sort('_id').limit(batch_size)
    products = await cursor.to_list(length=batch_size)
    return products

async def bulk_write_to_mongo(products):
    for product in products:
        product['_id'] = ObjectId()  # Generate a new ObjectId for each product

    try:
        result = await target_collection.insert_many(products, ordered=False)
        logger.info(f'Inserted {len(result.inserted_ids)} products into MongoDB.')
    except Exception as e:
        logger.error(f'Error inserting products into MongoDB: {e}')

async def process_batches(batch_size, concurrency_limit):
    tasks = []
    last_id = None
    while True:
        products = await fetch_products(batch_size, last_id)
        if not products:
            break
        last_id = products[-1]['_id']
        tasks.append(bulk_write_to_mongo(products))
        if len(tasks) >= concurrency_limit:
            await asyncio.gather(*tasks)
            tasks = []
    # Process remaining tasks if any
    if tasks:
        await asyncio.gather(*tasks)

async def main():
    batch_size = 1000
    concurrency_limit = 10

    start_time = time.time()
    await process_batches(batch_size, concurrency_limit)
    end_time = time.time()
    logger.info(f'Total time: {end_time - start_time:.2f} seconds.')

if __name__ == '__main__':
    asyncio.run(main())
