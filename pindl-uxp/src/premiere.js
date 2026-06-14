// Premiere DOM integration — import downloaded files into the active project.
// This is the value-add over the standalone tool.

let ppro;
try {
  ppro = require("premierepro");
} catch {
  ppro = null;
}

// Import absolute file paths into the active project's root bin.
// Returns count imported. No-op (returns 0) if no project is open.
async function importFiles(nativePaths, binName) {
  if (!ppro) throw new Error("premierepro module unavailable (run inside Premiere Pro).");
  if (!nativePaths.length) return 0;

  const project = await ppro.Project.getActiveProject();
  if (!project) throw new Error("No active Premiere project. Open a project first.");

  const rootItem = await project.getRootItem();

  // Optionally drop everything into a named bin so imports stay tidy.
  let target = rootItem;
  if (binName) {
    target = await findOrCreateBin(project, rootItem, binName);
  }

  // Premiere UXP import API. Signature across recent versions:
  //   project.importFiles(paths, suppressUI, targetBin, importAsNumberedStills)
  const ok = await project.importFiles(nativePaths, true, target, false);
  if (!ok) throw new Error("importFiles returned false.");
  return nativePaths.length;
}

async function findOrCreateBin(project, rootItem, binName) {
  const children = await rootItem.getItems();
  for (const child of children) {
    // ProjectItem name + type vary by version; match by name defensively.
    const name = typeof child.getName === "function" ? await child.getName() : child.name;
    if (name === binName) return child;
  }
  // createBin lives on the project in recent UXP builds.
  return await project.createBin(binName, rootItem);
}

function isAvailable() {
  return !!ppro;
}

module.exports = { importFiles, isAvailable };
