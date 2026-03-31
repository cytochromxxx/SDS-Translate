from flask import Blueprint, jsonify, request, send_file, send_from_directory
from ghs_pictogram_manager import GHSPictogramManager
import os

ghs_bp = Blueprint('ghs', __name__)

pictogram_manager = GHSPictogramManager()

@ghs_bp.route('/api/ghs/pictograms', methods=['GET'])
def get_ghs_pictograms():
    hazard_class = request.args.get('class', None)
    pictograms = pictogram_manager.get_all_pictograms()
    if hazard_class:
        pictograms = [p for p in pictograms if p.get('hazard_class') == hazard_class]
    return jsonify(pictograms)

@ghs_bp.route('/api/ghs/pictograms/<code>', methods=['GET'])
def get_ghs_pictogram(code):
    pictogram = pictogram_manager.get_pictogram_by_code(code)
    if pictogram:
        return jsonify(pictogram)
    return jsonify({'error': 'Pictogram not found'}), 404

@ghs_bp.route('/api/ghs/pictograms/<code>/svg')
def get_ghs_pictogram_svg(code):
    pictogram = pictogram_manager.get_pictogram_by_code(code)
    if pictogram and pictogram.get('svg_path'):
        svg_path = pictogram['svg_path']
        if os.path.exists(svg_path):
            return send_file(svg_path, mimetype='image/svg+xml')

    png_path = os.path.join('ghs', f'{code.lower()}.png')
    if os.path.exists(png_path):
        return send_file(png_path, mimetype='image/png')

    return jsonify({'error': 'Pictogram not found'}), 404

@ghs_bp.route('/ghs/<path:filename>')
def serve_ghs_image(filename):
    """Serve GHS pictogram PNG files directly from the ghs folder."""
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ghs'),
        filename
    )
