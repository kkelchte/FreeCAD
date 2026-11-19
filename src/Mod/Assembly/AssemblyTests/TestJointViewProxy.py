# SPDX-License-Identifier: LGPL-2.1-or-later
# /****************************************************************************
#                                                                           *
#    This file is part of FreeCAD.                                          *
#                                                                           *
#    FreeCAD is free software: you can redistribute it and/or modify it     *
#    under the terms of the GNU Lesser General Public License as            *
#    published by the Free Software Foundation, either version 2.1 of the   *
#    License, or (at your option) any later version.                        *
#                                                                           *
#    FreeCAD is distributed in the hope that it will be useful, but         *
#    WITHOUT ANY WARRANTY; without even the implied warranty of             *
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU       *
#    Lesser General Public License for more details.                        *
#                                                                           *
#    You should have received a copy of the GNU Lesser General Public       *
#    License along with FreeCAD. If not, see                                *
#    <https://www.gnu.org/licenses/>.                                       *
#                                                                           *
# ***************************************************************************/

"""A joint whose view provider is not restored must still recompute.

When a document is opened partially (as a dependency of another document), the
Python view provider of a joint is not restored: ``ViewObject.Proxy`` holds a
placeholder (an int) instead of a ``ViewProviderJoint``. Recomputing such a joint
raised ``'int' object has no attribute 'redrawJointPlacements'``.
"""

import types
import unittest

import FreeCAD as App
import JointObject


class _Tracker:
    """A view provider that records redraw calls."""

    def __init__(self):
        self.calls = 0

    def redrawJointPlacements(self, joint):
        self.calls += 1


class _Part:
    """A part moved by the pre-solve (hashable, unlike SimpleNamespace)."""

    def __init__(self):
        self.Placement = App.Placement(App.Vector(1, 0, 0), App.Rotation())


def _joint(view_proxy):
    return types.SimpleNamespace(ViewObject=types.SimpleNamespace(Proxy=view_proxy))


def _proxy():
    # Skip Joint.__init__, which needs a real document object.
    return JointObject.Joint.__new__(JointObject.Joint)


class TestJointViewProxy(unittest.TestCase):
    def test_redraw_with_placeholder_view_proxy(self):
        # Must not raise: the placeholder has no redrawJointPlacements.
        _proxy().redrawJointPlacements(_joint(1))

    def test_redraw_with_view_provider(self):
        tracker = _Tracker()
        _proxy().redrawJointPlacements(_joint(tracker))
        self.assertEqual(tracker.calls, 1)

    def test_undo_presolve_with_placeholder_view_proxy(self):
        proxy = _proxy()
        part = _Part()
        proxy.partsMovedByPresolved = {part: App.Placement()}
        proxy.undoPreSolve(_joint(1))
        self.assertEqual(part.Placement.Base, App.Vector(0, 0, 0))
