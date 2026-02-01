import { ContextStoreClient } from '@rawe/context-store-sdk';
import { DOCUMENT_SERVER_URL } from '@/utils/constants';

export const contextStoreClient = new ContextStoreClient({
  baseUrl: DOCUMENT_SERVER_URL,
});
