import { Client, Account, Databases, Storage } from 'appwrite';
import { env } from '$env/dynamic/public';

const endpoint = env.PUBLIC_APPWRITE_ENDPOINT || 'https://appwrite.bogazici.app/v1';
const projectId = env.PUBLIC_APPWRITE_PROJECT_ID || 'boun-archive';

export const client = new Client();

client
    .setEndpoint(endpoint)
    .setProject(projectId);

export const account = new Account(client);
export const databases = new Databases(client);
export const storage = new Storage(client);
