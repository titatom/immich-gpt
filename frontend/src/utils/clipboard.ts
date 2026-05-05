export async function copySecretToClipboard(secret?: string): Promise<boolean> {
  if (!secret || !navigator.clipboard?.writeText) {
    return false;
  }

  try {
    await navigator.clipboard.writeText(secret);
    return true;
  } catch {
    return false;
  }
}
