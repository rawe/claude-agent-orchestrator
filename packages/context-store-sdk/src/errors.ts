export class ContextStoreError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ContextStoreError';
  }
}
