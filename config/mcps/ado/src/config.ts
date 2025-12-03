export interface Config {
  adoOrg: string;
  adoPat: string;
  port: number;
}

export function loadConfig(): Config {
  const adoOrg = process.env.ADO_ORG;
  const adoPat = process.env.ADO_PAT;
  const port = parseInt(process.env.PORT || '3000', 10);

  if (!adoOrg) {
    throw new Error('ADO_ORG environment variable is required');
  }

  if (!adoPat) {
    throw new Error('ADO_PAT environment variable is required');
  }

  if (isNaN(port) || port < 1 || port > 65535) {
    throw new Error('PORT must be a valid port number (1-65535)');
  }

  return {
    adoOrg,
    adoPat,
    port,
  };
}
