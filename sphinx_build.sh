#!/bin/bash
# Script to set up and build Sphinx documentation for GatheRing

echo "📚 Setting up Sphinx documentation for GatheRing..."

# Navigate to docs directory
cd docs || exit 1

# Install documentation dependencies
echo "📦 Installing Sphinx and dependencies..."
pip install -r requirements-docs.txt

# Create necessary directories
echo "📁 Creating documentation structure..."
mkdir -p _static _templates api/generated

# Create static CSS for custom styling
cat > _static/custom.css << 'EOF'
/* Custom styles for GatheRing documentation */
.wy-nav-content {
    max-width: 1200px;
}

/* Better code block styling */
.highlight {
    background: #f8f8f8;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
}

/* Improve table styling */
.rst-content table.docutils {
    border: 1px solid #e1e4e8;
}

.rst-content table.docutils td,
.rst-content table.docutils th {
    border: 1px solid #e1e4e8;
    padding: 8px 12px;
}

/* Add icons for different types */
.admonition-title:before {
    margin-right: 4px;
}

.note .admonition-title:before {
    content: "📝";
}

.warning .admonition-title:before {
    content: "⚠️";
}

.tip .admonition-title:before {
    content: "💡";
}

.important .admonition-title:before {
    content: "❗";
}
EOF

# Create a make.bat for Windows users
cat > make.bat << 'EOF'
@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

if "%1" == "" goto help

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found.
	goto end
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd
EOF

# Create requirements-docs.txt if not exists
if [ ! -f requirements-docs.txt ]; then
cat > requirements-docs.txt << 'EOF'
sphinx>=7.0
sphinx-rtd-theme>=2.0
sphinx-copybutton>=0.5
sphinx-autobuild>=2021.3
myst-parser>=2.0
sphinxcontrib-napoleon>=0.7
EOF
fi

# Build the documentation
echo "🏗️  Building HTML documentation..."
make clean
make html

echo "✅ Documentation setup complete!"
echo ""
echo "📖 To view the documentation:"
echo "   Open: docs/_build/html/index.html"
echo ""
echo "🔄 To rebuild documentation:"
echo "   cd docs && make html"
echo ""
echo "🚀 To serve documentation locally with auto-reload:"
echo "   cd docs && make livehtml"
echo ""
echo "📋 Available make targets:"
echo "   make html       - Build HTML documentation"
echo "   make latexpdf   - Build PDF documentation"
echo "   make clean      - Clean build directory"
echo "   make apidoc     - Generate API documentation"
echo "   make livehtml   - Serve with auto-reload"