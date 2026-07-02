import fs from 'node:fs';
import * as acorn from 'acorn';
import * as walk from 'acorn-walk';
import * as parse5 from 'parse5';
import postcss from 'postcss';

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = { files: {}, diagnostics: [] };

function diagnostic(path, kind, message, line = null, column = null) {
  result.diagnostics.push({ path, kind, message, line, column });
}

function parseJavaScript(path, source, offsetLine = 0) {
  let ast;
  try {
    ast = acorn.parse(source, {
      ecmaVersion: 'latest', sourceType: 'script', locations: true,
      allowHashBang: true, allowAwaitOutsideFunction: true,
    });
  } catch (scriptError) {
    try {
      ast = acorn.parse(source, {
        ecmaVersion: 'latest', sourceType: 'module', locations: true,
        allowHashBang: true,
      });
    } catch (moduleError) {
      const loc = moduleError.loc || scriptError.loc || {};
      diagnostic(path, 'javascript', moduleError.message, (loc.line || 1) + offsetLine, loc.column || 0);
      return { functions: [], domRefs: [] };
    }
  }
  const functions = ast.body
    .filter(node => node.type === 'FunctionDeclaration' && node.id)
    .map(node => ({ name: node.id.name, line: node.loc.start.line + offsetLine }));
  const domRefs = [];
  walk.simple(ast, {
    CallExpression(node) {
      if (node.callee?.type !== 'MemberExpression' || node.callee.computed) return;
      if (node.callee.property?.name !== 'getElementById') return;
      const arg = node.arguments?.[0];
      if (arg?.type === 'Literal' && typeof arg.value === 'string') {
        domRefs.push({ id: arg.value, line: node.loc.start.line + offsetLine });
      }
    },
  });
  return { functions, domRefs };
}

function walkHtml(node, visit) {
  visit(node);
  for (const child of node.childNodes || []) walkHtml(child, visit);
  if (node.content) walkHtml(node.content, visit);
}

function textContent(node) {
  return (node.childNodes || []).map(child => child.value || textContent(child)).join('');
}

for (const relativePath of request.files) {
  const fullPath = `${request.root}/${relativePath}`;
  const rawSource = fs.readFileSync(fullPath, 'utf8');
  const wrapper = request.wrappers?.[relativePath];
  const source = wrapper ? `${wrapper.prefix}\n${rawSource}\n${wrapper.suffix}` : rawSource;
  const wrapperOffset = wrapper ? -1 : 0;
  if (relativePath.endsWith('.js') || relativePath.endsWith('.mjs')) {
    result.files[relativePath] = { kind: 'javascript', ...parseJavaScript(relativePath, source, wrapperOffset) };
    continue;
  }
  if (relativePath.endsWith('.html')) {
    let document;
    try {
      document = parse5.parse(rawSource, {
        sourceCodeLocationInfo: true,
        onParseError(error) {
          diagnostic(relativePath, 'html', error.code, error.startLine, error.startCol);
        },
      });
    } catch (error) {
      diagnostic(relativePath, 'html', error.message);
      continue;
    }
    const ids = [];
    const scripts = [];
    const stylesheets = [];
    const functions = [];
    const domRefs = [];
    walkHtml(document, node => {
      const attrs = Object.fromEntries((node.attrs || []).map(attr => [attr.name, attr.value]));
      if (attrs.id) ids.push({ id: attrs.id, line: node.sourceCodeLocation?.startLine || null });
      if (node.nodeName === 'script') {
        scripts.push({ src: attrs.src || null, line: node.sourceCodeLocation?.startLine || null });
        if (!attrs.src) {
          const line = node.sourceCodeLocation?.startTag?.endLine || 0;
          const parsed = parseJavaScript(relativePath, textContent(node), line);
          functions.push(...parsed.functions);
          domRefs.push(...parsed.domRefs);
        }
      }
      if (node.nodeName === 'link' && attrs.rel === 'stylesheet' && attrs.href) {
        stylesheets.push({ href: attrs.href, line: node.sourceCodeLocation?.startLine || null });
      }
      if (node.nodeName === 'style') {
        try {
          postcss.parse(textContent(node), { from: relativePath });
        } catch (error) {
          diagnostic(relativePath, 'css', error.reason || error.message, error.line, error.column);
        }
      }
    });
    result.files[relativePath] = { kind: 'html', ids, scripts, stylesheets, functions, domRefs };
    continue;
  }
  if (relativePath.endsWith('.css')) {
    try {
      postcss.parse(rawSource, { from: relativePath });
      result.files[relativePath] = { kind: 'css' };
    } catch (error) {
      diagnostic(relativePath, 'css', error.reason || error.message, error.line, error.column);
      result.files[relativePath] = { kind: 'css' };
    }
  }
}

process.stdout.write(JSON.stringify(result));
