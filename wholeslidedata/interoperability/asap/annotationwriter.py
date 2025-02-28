import xml.etree.cElementTree as ET
from xml.dom import minidom

from wholeslidedata.annotation.types import PointAnnotation, PolygonAnnotation
from wholeslidedata.visualization.color import get_color

def write_polygon(annos, coordinates, index, label_name, label_color):
    anno = ET.SubElement(annos, "Annotation")
    anno.set("Name", "Annotation " + str(index))
    anno.set("Type", "Polygon")
    anno.set("PartOfGroup", label_name)
    anno.set("Color", label_color)

    coords = ET.SubElement(anno, "Coordinates")
    coords_mem = []
    ridx = 0
    for _, r in enumerate(coordinates):
        x = int(r[0])
        y = int(r[1])
        if (x, y) in coords_mem:
            continue
        coords_mem.append((x, y))

        coord = ET.SubElement(coords, "Coordinate")
        coord.set("Order", str(ridx))
        coord.set("X", str(x))
        coord.set("Y", str(y))
        ridx += 1


def write_point(annos, coordinates, index, label_name, label_color):
    anno = ET.SubElement(annos, "Annotation")
    anno.set("Name", "Annotation " + str(index))
    anno.set("Type", "Dot")
    anno.set("PartOfGroup", label_name)
    anno.set("Color", label_color)

    coords = ET.SubElement(anno, "Coordinates")
    ridx = 0
    for r in coordinates:
        x, y = r
        coord = ET.SubElement(coords, "Coordinate")
        coord.set("Order", str(ridx))
        coord.set("X", str(x))
        coord.set("Y", str(y))
        ridx += 1


def write_point_set(points, output_path,label_color="black"):
    # the root of the xml file.
    root = ET.Element("ASAP_Annotations")

    # writing each anno one by one.
    annos = ET.SubElement(root, "Annotations")

    # writing the last groups part
    anno_groups = ET.SubElement(root, "AnnotationGroups")

    index = 0
    anno = ET.SubElement(annos, "Annotation")
    anno.set("Name", "Annotation " + str(index))
    anno.set("Type", "PointSet")
    anno.set("PartOfGroup", points[0].label.name)
    anno.set("Color", label_color)

    coords = ET.SubElement(anno, "Coordinates")
    ridx = 0
    for annotation in points:
        x, y = annotation.center
        coord = ET.SubElement(coords, "Coordinate")
        coord.set("Order", str(ridx))
        coord.set("X", str(x))
        coord.set("Y", str(y))
        ridx += 1

    group = ET.SubElement(anno_groups, "Group")
    group.set("Name", points[0].label.name)
    group.set("PartOfGroup", "None")
    group.set("Color", label_color)
    attr = ET.SubElement(group, "Attributes")

    # writing to the xml file with indentation
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    with open(output_path, "w") as f:
        f.write(xmlstr)



def write_asap_annotation(annotations, output_path, scaling=1.0, color_map=None):
    # the root of the xml file.
    root = ET.Element("ASAP_Annotations")

    # writing each anno one by one.
    annos = ET.SubElement(root, "Annotations")

    # writing the last groups part
    anno_groups = ET.SubElement(root, "AnnotationGroups")

    labels = set()

    for annotation in annotations:
        label_name = annotation.label.name
        # label_color = annotation.label.color if annotation.label.color is not None else "black"
        label_color = get_color(annotation, color_map)
        index = annotation.index
        if isinstance(annotation, PolygonAnnotation):
            coordinates = annotation.coordinates * scaling
            write_polygon(annos, coordinates, index, label_name, label_color)
        elif isinstance(annotation, PointAnnotation):
            coordinates = annotation.coordinates * scaling
            write_point(annos, coordinates, index, label_name, label_color)
        else:
            raise ValueError("unsupported geometry", annotation)

        labels.add((label_name, label_color))

    for label, color in labels:
        group = ET.SubElement(anno_groups, "Group")
        group.set("Name", label)
        group.set("PartOfGroup", "None")
        group.set("Color", color)
        attr = ET.SubElement(group, "Attributes")

    # writing to the xml file with indentation
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    with open(output_path, "w") as f:
        f.write(xmlstr)