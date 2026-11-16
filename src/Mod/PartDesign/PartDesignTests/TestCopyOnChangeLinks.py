# SPDX-License-Identifier: LGPL-2.1-or-later

"""Links into a "Link Copy On Change" copy must follow every re-copy.

When the source of a Tracking link changes, the link gets a new copy with new object names. A
reference such as Body.Pocket.;<mapped>.Edge12 into the old copy must be rewritten at every level of
its path and still resolve to an edge.
"""

import os
import shutil
import tempfile
import unittest

import FreeCAD as App
import Part
import Sketcher


class TestCopyOnChangeLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = App.newDocument("CowSource")
        part = self.src.addObject("App::Part", "Part")
        part.addProperty("App::PropertyLength", "CutLength", "Cut")
        part.setPropertyStatus("CutLength", "CopyOnChange")
        part.CutLength = 100
        body = self.src.addObject("PartDesign::Body", "Body")
        part.addObject(body)
        box = self.src.addObject("PartDesign::AdditiveBox", "Box")
        body.addObject(box)
        box.setExpression("Length", "href(Part.CutLength)")
        box.Width = box.Height = 10
        sketch = self.src.addObject("Sketcher::SketchObject", "Sketch")
        body.addObject(sketch)
        sketch.AttachmentSupport = (box, ["Face6"])
        sketch.MapMode = "FlatFace"
        sketch.addGeometry(Part.Circle(App.Vector(5, 5, 0), App.Vector(0, 0, 1), 2))
        sketch.addConstraint(Sketcher.Constraint("Radius", 0, 2))
        pocket = self.src.addObject("PartDesign::Pocket", "Pocket")
        body.addObject(pocket)
        pocket.Profile = sketch
        pocket.Type = "ThroughAll"
        self.src.recompute()
        self.src.saveAs(os.path.join(self.tmp, "CowSource.FCStd"))

        self.asm = App.newDocument("CowAssembly")
        self.asm.saveAs(os.path.join(self.tmp, "CowAssembly.FCStd"))
        self.link = self.asm.addObject("App::Link", "Link")
        self.link.LinkedObject = part
        self.link.LinkCopyOnChange = "Tracking"
        self.link.CutLength = 80
        self.asm.recompute()
        self.asm.recompute()
        self.ref = self.asm.addObject("App::FeaturePython", "Ref")
        self.ref.addProperty("App::PropertyXLinkSub", "Target")

    def tearDown(self):
        App.closeDocument(self.asm.Name)
        App.closeDocument(self.src.Name)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy(self):
        part = self.link.LinkedObject
        body = [o for o in part.Group if o.isDerivedFrom("PartDesign::Body")][0]
        return body, body.Tip

    def pick(self, element):
        """Reference an element as the GUI does: mapped name plus indexed name."""
        body, tip = self.copy()
        mapped = tip.Shape.ElementReverseMap[element]
        self.ref.Target = (self.link, ["%s.%s.;%s.%s" % (body.Name, tip.Name, mapped, element)])
        self.asm.recompute()

    def recopy(self, length):
        self.src.getObject("Part").CutLength = length  # changes the source, so the link copies again
        self.src.recompute()
        self.asm.recompute()
        self.asm.recompute()

    def check(self, element):
        body, tip = self.copy()
        sub = self.ref.Target[1][0]
        self.assertTrue(sub.startswith("%s.%s." % (body.Name, tip.Name)), sub)
        self.assertTrue(sub.endswith(element), sub)
        self.assertFalse(self.link.getSubObject(sub).isNull(), sub)

    def testReferenceFollowsRecopy(self):
        edge = "Edge1"
        self.pick(edge)
        self.check(edge)
        for length in (120, 90, 110):
            self.recopy(length)
            self.check(edge)
