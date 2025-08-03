const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

module.exports = {
  mode: 'development',
  entry: './src/index.ts',
  devtool: 'inline-source-map',
  devServer: {
    static: './dist',
    port: 8082,
    hot: true,
    open: true
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
  },
  output: {
    filename: 'webauthn-client.dev.js',
    path: path.resolve(__dirname, 'dist'),
    clean: true,
    library: {
      name: 'WebAuthnClient',
      type: 'umd',
    },
    globalObject: 'this',
  },
  plugins: [
    new CleanWebpackPlugin(),
    new HtmlWebpackPlugin({
      template: './public/index.html',
      filename: 'index.html',
    }),
  ],
  externals: {
    '@simplewebauthn/browser': {
      commonjs: '@simplewebauthn/browser',
      commonjs2: '@simplewebauthn/browser',
      amd: '@simplewebauthn/browser',
      root: 'SimpleWebAuthnBrowser'
    }
  }
};